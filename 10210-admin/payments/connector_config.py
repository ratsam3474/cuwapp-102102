"""
Hyperswitch Connector Configuration
Store connector IDs and webhook URLs for reference
"""

class ConnectorConfig:
    """Hyperswitch connector configuration"""
    
    # Merchant ID
    MERCHANT_ID = "merchant_1754725141"
    
    # Configured Connectors
    CONNECTORS = {
        "stripe": {
            "id": "mca_qQpy0TEv2xr9YUubYgmE",
            "name": "Stripe",
            "webhook": "https://app.hyperswitch.io/api/webhooks/merchant_1754725141/mca_qQpy0TEv2xr9YUubYgmE",
            "payment_methods": ["credit", "debit"],
            "status": "active"
        },
        "paypal": {
            "id": "mca_qprBvJeihdVRFJgRsTw7",
            "name": "PayPal",
            "webhook": "https://app.hyperswitch.io/api/webhooks/merchant_1754725141/mca_qprBvJeihdVRFJgRsTw7",
            "payment_methods": ["paypal"],
            "status": "active"
        },
        "paystack": {
            "id": "mca_Qc02HtgNxsEp5RXG8zYS",
            "name": "Paystack",
            "webhook": "https://app.hyperswitch.io/api/webhooks/merchant_1754725141/mca_Qc02HtgNxsEp5RXG8zYS",
            "payment_methods": ["card", "bank_transfer", "mobile_money"],
            "regions": ["Africa"],
            "status": "active"
        },
        "coinbase": {
            "id": "mca_0gSm9Sm8vfe9gXgl7zNo",
            "name": "Coinbase Commerce",
            "webhook": "https://app.hyperswitch.io/api/webhooks/merchant_1754725141/mca_0gSm9Sm8vfe9gXgl7zNo",
            "payment_methods": ["crypto_currency"],
            "cryptocurrencies": ["BTC", "ETH", "USDC", "DAI", "BCH", "LTC", "DOGE"],
            "status": "active"
        }
    }
    
    @classmethod
    def get_connector_id(cls, connector_name: str) -> str:
        """Get connector ID by name"""
        connector = cls.CONNECTORS.get(connector_name.lower())
        return connector["id"] if connector else None
    
    @classmethod
    def get_webhook_url(cls, connector_name: str) -> str:
        """Get webhook URL for a connector"""
        connector = cls.CONNECTORS.get(connector_name.lower())
        return connector["webhook"] if connector else None
    
    @classmethod
    def get_active_connectors(cls) -> list:
        """Get list of active connectors"""
        return [
            name for name, config in cls.CONNECTORS.items() 
            if config.get("status") == "active"
        ]
    
    @classmethod
    def get_payment_methods(cls) -> set:
        """Get all available payment methods from active connectors"""
        methods = set()
        for connector in cls.CONNECTORS.values():
            if connector.get("status") == "active":
                methods.update(connector.get("payment_methods", []))
        return methods