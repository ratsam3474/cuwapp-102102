// Debug script to test navigation
console.log('Debug script loaded');

// Test if sections exist
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded');
    
    // Check if all sections exist
    const sections = ['sessions', 'chats', 'contacts', 'groups', 'campaigns', 'analytics', 'warmer'];
    sections.forEach(section => {
        const element = document.getElementById(`${section}-section`);
        if (element) {
            console.log(`✓ ${section}-section exists`);
        } else {
            console.error(`✗ ${section}-section NOT FOUND`);
        }
    });
    
    // Check if navigation links exist
    const navLinks = document.querySelectorAll('.nav-link');
    console.log(`Found ${navLinks.length} navigation links`);
    
    // Test showSection function
    window.testShowSection = function(sectionName) {
        console.log(`Testing showSection('${sectionName}')`);
        
        // Hide all sections
        sections.forEach(section => {
            const element = document.getElementById(`${section}-section`);
            if (element) {
                element.style.display = 'none';
                console.log(`  - Hidden ${section}-section`);
            }
        });
        
        // Show target section
        const target = document.getElementById(`${sectionName}-section`);
        if (target) {
            target.style.display = 'block';
            console.log(`  - Shown ${sectionName}-section`);
        } else {
            console.error(`  - Cannot show ${sectionName}-section - NOT FOUND`);
        }
    };
    
    // Add click handlers directly
    navLinks.forEach(link => {
        const onclick = link.getAttribute('onclick');
        if (onclick && onclick.includes('showSection')) {
            const section = onclick.match(/showSection\('(\w+)'\)/)?.[1];
            if (section) {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    console.log(`Nav clicked: ${section}`);
                    testShowSection(section);
                });
            }
        }
    });
});