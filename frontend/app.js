class SalesChatbot {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.isLoading = false;
        this.apiUrl = window.CHATBOT_API_URL || '';
        this.init();
    }

    generateSessionId() {
        return 'sales_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }

    init() {
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.chatMessages = document.getElementById('chat-messages');
        this.loading = document.getElementById('loading');
        this.charCount = document.getElementById('char-count');

        this.bindEvents();
        this.messageInput.focus();
    }

    bindEvents() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.messageInput.addEventListener('input', () => {
            this.updateCharCount();
            this.toggleSendButton();
        });

        // Auto-resize chat messages
        window.addEventListener('resize', () => {
            this.scrollToBottom();
        });
    }

    updateCharCount() {
        const count = this.messageInput.value.length;
        this.charCount.textContent = count;
        
        if (count > 450) {
            this.charCount.style.color = '#dc3545';
        } else if (count > 400) {
            this.charCount.style.color = '#fd7e14';
        } else {
            this.charCount.style.color = '#6c757d';
        }
    }

    toggleSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText || this.isLoading;
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message || this.isLoading) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input
        this.messageInput.value = '';
        this.updateCharCount();
        this.toggleSendButton();

        // Show loading
        this.setLoading(true);

        try {
            const response = await fetch(`${this.apiUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    message: message
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Add bot response
            this.addMessage(data.answer, 'bot', {
                sources: data.sources,
                usedChunks: data.used_chunks,
                latency: data.latency_ms
            });

        } catch (error) {
            console.error('Error:', error);
            this.addMessage(
                'Sorry, I encountered an error while processing your request. Please try again.',
                'bot'
            );
        } finally {
            this.setLoading(false);
            this.messageInput.focus();
        }
    }

    addMessage(content, type, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Format content (convert newlines to paragraphs)
        const formattedContent = this.formatContent(content);
        contentDiv.innerHTML = formattedContent;

        // Add sources if available
        if (metadata.sources && metadata.sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'sources';
            sourcesDiv.innerHTML = `
                <strong>Sources:</strong> ${metadata.sources.join(', ')} 
                <br><small>Used ${metadata.usedChunks} chunks • ${metadata.latency}ms</small>
            `;
            contentDiv.appendChild(sourcesDiv);
        }

        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);
        
        this.scrollToBottom();
    }

    formatContent(content) {
        // Convert markdown-style formatting
        return content
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^\s*/, '<p>')
            .replace(/\s*$/, '</p>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }

    setLoading(loading) {
        this.isLoading = loading;
        this.loading.classList.toggle('hidden', !loading);
        this.toggleSendButton();
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
}

// Widget version for embedding
class SalesChatbotWidget {
    static init(config = {}) {
        this.endpoint = config.endpoint || (window.CHATBOT_API_URL ? window.CHATBOT_API_URL + '/chat' : '/chat');
            title: 'Sales Assistant 🤖',
            subtitle: 'Query previous client meetings',
            position: 'bottom-right'
        };

        const finalConfig = { ...defaultConfig, ...config };
        
        // Create widget HTML
        const widgetHTML = `
            <div id="sales-chatbot-widget" class="chatbot-widget ${finalConfig.position}">
                <div class="chatbot-toggle" id="chatbot-toggle">
                    <span class="chatbot-icon">💬</span>
                </div>
                <div class="chatbot-container" id="chatbot-container">
                    <div class="chatbot-header">
                        <h3>${finalConfig.title}</h3>
                        <p>${finalConfig.subtitle}</p>
                        <button class="chatbot-close" id="chatbot-close">×</button>
                    </div>
                    <div class="chatbot-messages" id="chatbot-messages">
                        <div class="message bot-message">
                            <div class="message-content">
                                <p>Hello! I can help you find information from previous client meetings. What would you like to know?</p>
                            </div>
                        </div>
                    </div>
                    <div class="chatbot-input">
                        <input type="text" id="chatbot-input" placeholder="Ask about client meetings...">
                        <button id="chatbot-send">Send</button>
                    </div>
                </div>
            </div>
        `;

        // Add widget to page
        document.body.insertAdjacentHTML('beforeend', widgetHTML);
        
        // Initialize widget functionality
        new SalesChatbotWidgetController(finalConfig);
    }
}

class SalesChatbotWidgetController {
    constructor(config) {
        this.config = config;
        this.sessionId = 'widget_' + Math.random().toString(36).substr(2, 9);
        this.isOpen = false;
        this.isLoading = false;
        
        this.initElements();
        this.bindEvents();
    }

    initElements() {
        this.toggle = document.getElementById('chatbot-toggle');
        this.container = document.getElementById('chatbot-container');
        this.close = document.getElementById('chatbot-close');
        this.messages = document.getElementById('chatbot-messages');
        this.input = document.getElementById('chatbot-input');
        this.send = document.getElementById('chatbot-send');
    }

    bindEvents() {
        this.toggle.addEventListener('click', () => this.toggleWidget());
        this.close.addEventListener('click', () => this.closeWidget());
        this.send.addEventListener('click', () => this.sendMessage());
        
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
    }

    toggleWidget() {
        this.isOpen = !this.isOpen;
        this.container.classList.toggle('open', this.isOpen);
        
        if (this.isOpen) {
            this.input.focus();
        }
    }

    closeWidget() {
        this.isOpen = false;
        this.container.classList.remove('open');
    }

    async sendMessage() {
        const message = this.input.value.trim();
        if (!message || this.isLoading) return;

        this.addMessage(message, 'user');
        this.input.value = '';
        this.setLoading(true);

        try {
            const response = await fetch(this.config.endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    message: message
                })
            });

            const data = await response.json();
            this.addMessage(data.answer, 'bot');

        } catch (error) {
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        } finally {
            this.setLoading(false);
        }
    }

    addMessage(content, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        messageDiv.innerHTML = `<div class="message-content"><p>${content}</p></div>`;
        
        this.messages.appendChild(messageDiv);
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    setLoading(loading) {
        this.isLoading = loading;
        this.send.disabled = loading;
        this.send.textContent = loading ? '...' : 'Send';
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on the main chatbot page
    if (document.getElementById('chat-messages')) {
        new SalesChatbot();
    }
});

// Export for widget usage
window.SalesChatbotWidget = SalesChatbotWidget;