"""
LangChain Agent Factory and Orchestrator
Creates root agents with sub-agents for each trigger using LangGraph
"""
from typing import Dict, List, Optional, Any, Annotated, TypedDict
import asyncio
import logging
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from agent_builder.models.agent import Agent, TriggerType
from agent_builder.core.tool_wrappers import WahaToolWrapper, BuiltinToolWrapper, CustomToolWrapper

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """State for the agent graph"""
    messages: Annotated[List, add_messages]
    trigger_type: str
    webhook_data: Dict[str, Any]
    session_context: Dict[str, Any]
    current_agent: str

class TriggerSubAgent:
    """Sub-agent for handling specific WhatsApp trigger events"""
    
    def __init__(self, trigger_type: TriggerType, config: dict):
        self.trigger_type = trigger_type
        self.name = f"trigger_{trigger_type.value}_agent"
        self.description = f"Handles {trigger_type.value} events"
        self.model = config.get('model', 'gemini-1.5-flash')
        self.instructions = config.get('instruction', '')
        self.temperature = float(config.get('temperature', 0.7))
        
        # Prepare tools
        self.tools = self._prepare_tools(config.get('tools', {}))
        
        # Create LLM
        self.llm = ChatGoogleGenerativeAI(
            model=self.model,
            temperature=self.temperature
        )
        
        # Create prompt
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.instructions or f"You are a WhatsApp agent handling {trigger_type.value} events."),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create agent
        self.agent = create_structured_chat_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create executor
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
    
    def _prepare_tools(self, tool_config: dict) -> List:
        """Convert tool configuration to LangChain-compatible tools"""
        tools = []
        
        # Add WAHA tools
        for tool_id in tool_config.get('waha_tools', []):
            tool = WahaToolWrapper.create_tool(tool_id)
            if tool:
                tools.append(tool)
        
        # Add built-in tools
        for tool_name in tool_config.get('builtin_tools', []):
            tool = BuiltinToolWrapper.create_tool(tool_name)
            if tool:
                tools.append(tool)
        
        # TODO: Add MCP and custom tools
        
        return tools
    
    async def process(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook data"""
        try:
            # Format input based on trigger type
            if self.trigger_type == TriggerType.MESSAGE:
                input_text = f"New message from {webhook_data.get('from', 'unknown')}: {webhook_data.get('body', '')}"
            else:
                input_text = f"Event {self.trigger_type.value}: {webhook_data}"
            
            # Run the agent
            result = await self.executor.ainvoke({"input": input_text})
            
            return {
                "success": True,
                "output": result.get("output", ""),
                "agent": self.name
            }
        except Exception as e:
            logger.error(f"Error in sub-agent {self.name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }

class RootOrchestrator:
    """Root agent that coordinates all sub-agents based on triggers using LangGraph"""
    
    def __init__(self, agent_config: Agent):
        self.agent_config = agent_config
        self.sub_agents: Dict[str, TriggerSubAgent] = {}
        self.session_data: Dict[str, Any] = {}
        
        # Create sub-agents for each trigger
        self._create_sub_agents()
        
        # Create the workflow graph
        self._create_workflow()
    
    def _create_sub_agents(self):
        """Create sub-agents for each configured trigger"""
        for trigger in self.agent_config.triggers:
            config = {
                'model': self.agent_config.model,
                'temperature': self.agent_config.temperature,
                'instruction': self.agent_config.trigger_instructions.get(trigger, ''),
                'tools': {
                    'waha_tools': self.agent_config.waha_tools or [],
                    'builtin_tools': self.agent_config.builtin_tools or [],
                    'mcp_tools': self.agent_config.mcp_tools or [],
                    'custom_tools': self.agent_config.custom_tools or []
                }
            }
            self.sub_agents[trigger] = TriggerSubAgent(trigger, config)
    
    def _create_workflow(self):
        """Create LangGraph workflow"""
        # Define the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes for each sub-agent
        for trigger, agent in self.sub_agents.items():
            workflow.add_node(trigger, self._create_agent_node(agent))
        
        # Add routing logic
        def route_to_agent(state: AgentState) -> str:
            """Route to the appropriate sub-agent based on trigger type"""
            trigger_type = state.get("trigger_type")
            if trigger_type in self.sub_agents:
                return trigger_type
            return END
        
        # Set entry point
        workflow.set_entry_point("router")
        workflow.add_node("router", route_to_agent)
        
        # Add edges from router to sub-agents
        for trigger in self.sub_agents:
            workflow.add_edge("router", trigger)
            workflow.add_edge(trigger, END)
        
        # Compile the graph
        self.app = workflow.compile()
    
    def _create_agent_node(self, agent: TriggerSubAgent):
        """Create a node function for a sub-agent"""
        async def agent_node(state: AgentState) -> AgentState:
            webhook_data = state["webhook_data"]
            result = await agent.process(webhook_data)
            
            # Update state with result
            state["messages"].append({
                "role": "assistant",
                "content": result.get("output", ""),
                "agent": agent.name
            })
            
            return state
        
        return agent_node
    
    async def run_async(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main orchestration logic"""
        trigger_type = input_data.get('trigger_type')
        webhook_data = input_data.get('webhook_data', {})
        
        # Add context about the session
        webhook_data['session_context'] = self.session_data
        webhook_data['timestamp'] = datetime.now().isoformat()
        
        # Check if we have a handler for this trigger
        if trigger_type not in self.sub_agents:
            return {
                'success': False,
                'error': f"No handler for trigger: {trigger_type}",
                'agent_id': self.agent_config.id
            }
        
        try:
            # Create initial state
            initial_state = {
                "messages": [],
                "trigger_type": trigger_type,
                "webhook_data": webhook_data,
                "session_context": self.session_data,
                "current_agent": ""
            }
            
            # Run the workflow
            final_state = await self.app.ainvoke(initial_state)
            
            # Extract result from final state
            if final_state["messages"]:
                last_message = final_state["messages"][-1]
                return {
                    'success': True,
                    'trigger': trigger_type,
                    'result': last_message.get("content", ""),
                    'agent_id': self.agent_config.id
                }
            else:
                return {
                    'success': False,
                    'error': "No response from agent",
                    'trigger': trigger_type,
                    'agent_id': self.agent_config.id
                }
                
        except Exception as e:
            logger.error(f"Orchestrator error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'trigger': trigger_type,
                'agent_id': self.agent_config.id
            }
    
    def update_session_data(self, data: Dict[str, Any]):
        """Update session context data"""
        self.session_data.update(data)

class AgentFactory:
    """Factory for creating and managing LangChain agents"""
    
    @staticmethod
    def create_agent(agent_config: Agent) -> RootOrchestrator:
        """Create a root orchestrator with sub-agents from database config"""
        return RootOrchestrator(agent_config)
    
    @staticmethod
    async def test_agent(agent: RootOrchestrator, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test an agent with sample data"""
        return await agent.run_async(test_data)