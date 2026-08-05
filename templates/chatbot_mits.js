// Document elements
const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const typingIndicator = document.getElementById('typingIndicator');
const clearChatBtn = document.getElementById('clearChatBtn');
const sidebar = document.getElementById('sidebar');
const menuToggleBtn = document.getElementById('menuToggleBtn');
const closeSidebarBtn = document.getElementById('closeSidebarBtn');
const userNameText = document.getElementById('userNameText');
const userIdText = document.getElementById('userIdText');
const toastElement = document.getElementById('toast');
const welcomeTimeElement = document.getElementById('welcomeTime');
const suggestionChips = document.querySelectorAll('.suggestion-chip');

// Verification DOM elements
const authOverlay = document.getElementById('authOverlay');
const authStepMobile = document.getElementById('authStepMobile');
const authStepOtp = document.getElementById('authStepOtp');
const authMobileInput = document.getElementById('authMobileInput');
const authOtpInput = document.getElementById('authOtpInput');
const authSendBtn = document.getElementById('authSendBtn');
const authVerifyBtn = document.getElementById('authVerifyBtn');
const authBackBtn = document.getElementById('authBackBtn');

// Global variables
let userId = '';
let mobileNumber = '';
let conversationHistory = [];

// Initialize Page
document.addEventListener('DOMContentLoaded', () => {
    // Set timestamp for welcome message
    const now = new Date();
    welcomeTimeElement.textContent = formatTime(now);

    // Set up user identification
    initUser();

    // Register event listeners
    chatForm.addEventListener('submit', handleFormSubmit);
    clearChatBtn.addEventListener('click', handleClearChat);
    menuToggleBtn.addEventListener('click', toggleSidebar);
    closeSidebarBtn.addEventListener('click', toggleSidebar);

    // Verification listeners
    authSendBtn.addEventListener('click', handleSendOtp);
    authVerifyBtn.addEventListener('click', handleVerifyOtp);
    authBackBtn.addEventListener('click', handleBackToMobile);

    // Setup suggestion chip clicks
    suggestionChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.getAttribute('data-query');
            if (query) {
                sendUserMessage(query);
                // On mobile, close the sidebar after selecting a chip
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('open');
                }
            }
        });
    });

    // Auto-adjust layout on resize
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            sidebar.classList.remove('open');
        }
    });
});

// Setup user identity and fetch previous chat
async function initUser() {
    // Try to retrieve user details from localStorage
    let storedUserId = localStorage.getItem('mits_chat_user_id');
    let storedUserName = localStorage.getItem('mits_chat_user_name');
    let isVerified = localStorage.getItem('mits_chat_verified') === 'true';

    if (!storedUserId) {
        // Generate random ID
        const randomNum = Math.floor(1000 + Math.random() * 9000);
        storedUserId = `mits-student-${randomNum}`;
        storedUserName = `Student #${randomNum}`;
        
        localStorage.setItem('mits_chat_user_id', storedUserId);
        localStorage.setItem('mits_chat_user_name', storedUserName);
    }

    userId = storedUserId;
    userNameText.textContent = storedUserName;
    userIdText.textContent = `ID: ${storedUserId}`;

    if (isVerified) {
        authOverlay.classList.add('hidden');
        mobileNumber = localStorage.getItem('mits_chat_mobile') || '';
    } else {
        authOverlay.classList.remove('hidden');
    }

    // Load conversation history
    await loadConversation();
}

// Send OTP handler
async function handleSendOtp() {
    const inputVal = authMobileInput.value.trim();
    if (!/^[0-9]{10}$/.test(inputVal)) {
        showToast('Please enter a valid 10-digit mobile number');
        return;
    }

    mobileNumber = inputVal;
    authSendBtn.disabled = true;
    authSendBtn.textContent = 'Sending...';

    // Fast local simulation mode if opened via file:// protocol
    const isFileProtocol = window.location.protocol === 'file:';

    if (isFileProtocol) {
        setTimeout(() => {
            const mockOtp = Math.floor(1000 + Math.random() * 9000).toString();
            localStorage.setItem('mits_mock_otp', mockOtp);
            showToast(`[TEST MODE] OTP Sent! Code: ${mockOtp}`);
            authStepMobile.classList.add('hidden');
            authStepOtp.classList.remove('hidden');
            authOtpInput.focus();
            authSendBtn.disabled = false;
            authSendBtn.textContent = 'Send Verification Code';
        }, 200);
        return;
    }

    try {
        const response = await fetch('/api/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mobileNumber })
        });

        const data = await response.json();
        
        if (response.ok && data.success) {
            showToast(`OTP Sent! Code: ${data.otp}`);
            authStepMobile.classList.add('hidden');
            authStepOtp.classList.remove('hidden');
            authOtpInput.focus();
        } else {
            showToast(data.error || 'Failed to send OTP code');
        }
    } catch (err) {
        console.warn('Network issue, switching to instant offline OTP fallback...', err);
        // Offline / dev fallback mode
        const mockOtp = Math.floor(1000 + Math.random() * 9000).toString();
        localStorage.setItem('mits_mock_otp', mockOtp);
        showToast(`[OFFLINE MODE] OTP Sent! Code: ${mockOtp}`);
        authStepMobile.classList.add('hidden');
        authStepOtp.classList.remove('hidden');
        authOtpInput.focus();
    } finally {
        authSendBtn.disabled = false;
        authSendBtn.textContent = 'Send Verification Code';
    }
}

// Verify OTP handler
async function handleVerifyOtp() {
    const otp = authOtpInput.value.trim();
    if (!/^[0-9]+$/.test(otp)) {
        showToast('Please enter a valid verification code');
        return;
    }

    authVerifyBtn.disabled = true;
    authVerifyBtn.textContent = 'Verifying...';

    const isFileProtocol = window.location.protocol === 'file:';
    const mockOtp = localStorage.getItem('mits_mock_otp');

    // Local validation check
    if (isFileProtocol || mockOtp) {
        showToast('Mobile verified successfully (Local Mode)!');
        localStorage.setItem('mits_chat_verified', 'true');
        localStorage.setItem('mits_chat_mobile', mobileNumber);
        localStorage.removeItem('mits_mock_otp');
        
        authOverlay.style.opacity = '0';
        setTimeout(() => {
            authOverlay.classList.add('hidden');
        }, 400);
        
        // Try saving to DB in background (no-block)
        try {
            fetch('/api/verify-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId, mobileNumber, otp })
            }).catch(e => console.log('Offline server sync skipped'));
        } catch(e) {}
        
        authVerifyBtn.disabled = false;
        authVerifyBtn.textContent = 'Verify & Start Chat';
        return;
    }    try {
        const response = await fetch('/api/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId, mobileNumber, otp })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showToast('Mobile verified successfully!');
            localStorage.setItem('mits_chat_verified', 'true');
            localStorage.setItem('mits_chat_mobile', mobileNumber);
            if (data.token) {
                localStorage.setItem('mits_chat_jwt_token', data.token);
            }
            
            // Unlocked state transition animation
            authOverlay.style.opacity = '0';
            setTimeout(() => {
                authOverlay.classList.add('hidden');
            }, 400);
        } else {
            showToast(data.detail || data.error || 'Invalid OTP code');
        }
    } catch (err) {
        console.error('Error verifying OTP:', err);
        showToast('Network error while verifying OTP');
    } finally {
        authVerifyBtn.disabled = false;
        authVerifyBtn.textContent = 'Verify & Start Chat';
    }
}

// Back button handler
function handleBackToMobile() {
    authOtpInput.value = '';
    localStorage.removeItem('mits_mock_otp');
    authStepOtp.classList.add('hidden');
    authStepMobile.classList.remove('hidden');
    authMobileInput.focus();
}

// Format time
function formatTime(date) {
    let hours = date.getHours();
    let minutes = date.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12; // key '0' as '12'
    minutes = minutes < 10 ? '0' + minutes : minutes;
    return `${hours}:${minutes} ${ampm}`;
}

// Show Toast message
function showToast(message) {
    toastElement.textContent = message;
    toastElement.classList.add('show');
    setTimeout(() => {
        toastElement.classList.remove('show');
    }, 3000);
}

// Append new message to chat UI
function appendMessage(sender, text, timestamp = new Date()) {
    const wrapper = document.createElement('div');
    wrapper.classList.add('message-wrapper', sender);

    // Avatar
    const avatar = document.createElement('div');
    avatar.classList.add('message-avatar');
    avatar.textContent = sender === 'user' ? '👤' : '🤖';

    // Bubble Container
    const bubbleContainer = document.createElement('div');
    bubbleContainer.classList.add('message-bubble-container');

    // Bubble
    const bubble = document.createElement('div');
    bubble.classList.add('message-bubble');
    bubble.innerHTML = formatMarkdownText(text);

    // Time
    const time = document.createElement('span');
    time.classList.add('message-time');
    time.textContent = typeof timestamp === 'string' ? timestamp : formatTime(timestamp);

    bubbleContainer.appendChild(bubble);
    bubbleContainer.appendChild(time);
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubbleContainer);

    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Markdown Formatter Helper
function formatMarkdownText(text) {
    if (!text) return '';
    
    // Replace double asterisks with strong tags
    let html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Replace links formatted as click here
    html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // Handle bullet points
    if (html.includes('\n- ')) {
        const lines = html.split('\n');
        let inList = false;
        let processedLines = [];
        
        lines.forEach(line => {
            if (line.trim().startsWith('- ')) {
                if (!inList) {
                    processedLines.push('<ul>');
                    inList = true;
                }
                processedLines.push(`<li>${line.trim().substring(2)}</li>`);
            } else {
                if (inList) {
                    processedLines.push('</ul>');
                    inList = false;
                }
                processedLines.push(line);
            }
        });
        
        if (inList) {
            processedLines.push('</ul>');
        }
        
        html = processedLines.join('\n');
    }

    // Replace newlines with break tags
    html = html.replace(/\n/g, '<br/>');
    
    return html;
}

// Toggle Sidebar for Mobile
function toggleSidebar() {
    sidebar.classList.toggle('open');
}

// Handle Form Submission
function handleFormSubmit(e) {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    chatInput.value = '';
    sendUserMessage(query);
}

// Helper to append a placeholder for streaming message
function appendStreamingPlaceholder(sender, timestamp = new Date()) {
    const wrapper = document.createElement('div');
    wrapper.classList.add('message-wrapper', sender);

    // Avatar
    const avatar = document.createElement('div');
    avatar.classList.add('message-avatar');
    avatar.textContent = sender === 'user' ? '👤' : '🤖';

    // Bubble Container
    const bubbleContainer = document.createElement('div');
    bubbleContainer.classList.add('message-bubble-container');

    // Bubble with cursor/dot
    const bubble = document.createElement('div');
    bubble.classList.add('message-bubble');
    bubble.innerHTML = '<span class="dot-typing"></span>';

    // Time
    const time = document.createElement('span');
    time.classList.add('message-time');
    time.textContent = typeof timestamp === 'string' ? timestamp : formatTime(timestamp);

    bubbleContainer.appendChild(bubble);
    bubbleContainer.appendChild(time);
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubbleContainer);

    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return { bubble, time };
}

// Process sending a user message with Streaming
async function sendUserMessage(query) {
    // Append user message
    const timestamp = new Date();
    appendMessage('user', query, timestamp);

    // Save to history
    conversationHistory.push({ sender: 'user', text: query, timestamp: timestamp.toISOString() });

    // Show typing indicator
    typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;

    const isFileProtocol = window.location.protocol === 'file:';
    let responseText = '';

    if (isFileProtocol) {
        // Fast local simulation mode if opened via file:// protocol
        await new Promise(resolve => setTimeout(resolve, 600));
        typingIndicator.style.display = 'none';

        const responseTextFull = searchKnowledgeBase(query);
        const { bubble } = appendStreamingPlaceholder('bot');

        // Simulate streaming locally for smooth visual flow
        const words = responseTextFull.split(' ');
        let accumulated = "";
        for (let i = 0; i < words.length; i++) {
            accumulated += (i === 0 ? "" : " ") + words[i];
            bubble.innerHTML = formatMarkdownText(accumulated);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            await new Promise(resolve => setTimeout(resolve, 40));
        }
        responseText = responseTextFull;
    } else {
        try {
            const response = await fetch('/api/chat-stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            if (!response.ok) {
                throw new Error('API server returned error');
            }

            typingIndicator.style.display = 'none';
            const { bubble } = appendStreamingPlaceholder('bot');

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                
                // Keep the last incomplete line in the buffer
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const parsed = JSON.parse(line);
                        if (parsed.sources) {
                            console.log("[RAG Sources]:", parsed.sources);
                        } else if (parsed.text) {
                            responseText += parsed.text;
                            bubble.innerHTML = formatMarkdownText(responseText);
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                    } catch (e) {
                        console.warn("Failed to parse stream line:", line, e);
                    }
                }
            }

            // Flush remaining buffer
            if (buffer.trim()) {
                try {
                    const parsed = JSON.parse(buffer);
                    if (parsed.text) {
                        responseText += parsed.text;
                        bubble.innerHTML = formatMarkdownText(responseText);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                } catch (e) {}
            }

        } catch (err) {
            console.warn('RAG streaming failed, falling back to local offline search...', err);
            typingIndicator.style.display = 'none';
            responseText = searchKnowledgeBase(query);
            appendMessage('bot', responseText, new Date());
        }
    }

    const botTimestamp = new Date();
    
    // Add to history
    conversationHistory.push({ sender: 'bot', text: responseText, timestamp: botTimestamp.toISOString() });

    // Save conversation to DB/local storage
    await saveConversation();
}
// Session Expiry Helper
function handleAuthExpiry() {
    localStorage.removeItem('mits_chat_verified');
    localStorage.removeItem('mits_chat_jwt_token');
    authOverlay.classList.remove('hidden');
    authOverlay.style.opacity = '1';
    authStepOtp.classList.add('hidden');
    authStepMobile.classList.remove('hidden');
    showToast('Session expired. Please verify with OTP again.');
}

// Load Conversation from API or Local Storage Fallback
async function loadConversation() {
    try {
        const token = localStorage.getItem('mits_chat_jwt_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const response = await fetch(`/api/conversations/${userId}`, { headers });
        
        if (response.status === 401 || response.status === 403) {
            handleAuthExpiry();
            return;
        }
        if (!response.ok) throw new Error('Database server issue');
        
        const data = await response.json();
        if (data.conversation && data.conversation.length > 0) {
            conversationHistory = data.conversation;
            renderHistory();
            showToast('Conversation loaded from database');
            return;
        }
    } catch (err) {
        console.warn('Failed to load conversation from database API, trying local storage...', err);
    }

    // Local Storage Fallback
    const localData = localStorage.getItem(`mits_conversation_${userId}`);
    if (localData) {
        try {
            conversationHistory = JSON.parse(localData);
            renderHistory();
            showToast('Conversation loaded from local storage');
        } catch (e) {
            console.error('Error parsing local storage history', e);
        }
    }
}

// Save Conversation to API or Local Storage Fallback
async function saveConversation() {
    // Save to local storage first for speed and local assurance
    localStorage.setItem(`mits_conversation_${userId}`, JSON.stringify(conversationHistory));

    try {
        const token = localStorage.getItem('mits_chat_jwt_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch('/api/conversations', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ userId: userId, conversation: conversationHistory })
        });
        
        if (response.status === 401 || response.status === 403) {
            handleAuthExpiry();
            return;
        }
        if (!response.ok) throw new Error('Database write error');
        console.log('Conversation backed up to server database');
    } catch (err) {
        console.warn('Failed to back up conversation to server. Saved locally.', err);
    }
}

// Clear History Handler
async function handleClearChat() {
    if (confirm('Are you sure you want to clear your chat history?')) {
        conversationHistory = [];
        
        // Clear local storage
        localStorage.removeItem(`mits_conversation_${userId}`);

        // Update database (save empty array)
        try {
            const token = localStorage.getItem('mits_chat_jwt_token');
            const headers = { 'Content-Type': 'application/json' };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch('/api/conversations', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ userId: userId, conversation: [] })
            });

            if (response.status === 401 || response.status === 403) {
                handleAuthExpiry();
                return;
            }
        } catch (err) {
            console.warn('Failed to clear database conversation. Cleared locally.', err);
        }

        // Reset Chat UI (Keep only initial welcome message)
        const firstMessage = chatMessages.firstElementChild;
        chatMessages.innerHTML = '';
        if (firstMessage) {
            chatMessages.appendChild(firstMessage);
        }
        showToast('Chat history cleared');
    }
}
// Render Conversation History from loaded array
function renderHistory() {
    // Clear everything except welcome message
    const firstMessage = chatMessages.firstElementChild;
    chatMessages.innerHTML = '';
    if (firstMessage) {
        chatMessages.appendChild(firstMessage);
    }

    // Append history items
    conversationHistory.forEach(msg => {
        appendMessage(msg.sender, msg.text, new Date(msg.timestamp));
    });
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/* ==========================================================================
   LOCAL KNOWLEDGE BASE & RETRIEVAL (MOCK RAG ENGINE)
   Compiled from MITS dataset: dataset/home.txt and dataset/ai_ml_faculty.txt
   ========================================================================== */

const KNOWLEDGE_BASE = [
    {
        keywords: ['rank', 'ranking', 'nirf', 'rating', 'star', 'accreditation', 'naac', 'nba', 'achieve', 'award', 'iste'],
        response: 'Madanapalle Institute of Technology & Science (MITS) holds notable rankings and awards:\n' +
            '- **NAAC Accreditation**: Holds prestigious **NAAC A+ accreditation**.\n' +
            '- **Deemed University**: Conferred the status of **Deemed to be University** on July 15, 2025.\n' +
            '- **NIRF Rankings 2025**: Secured a position in the **201-300 band** under the Engineering Category.\n' +
            '- **ISTE Award**: Won the **ISTE Best Engineering College Award - 2024** by the Indian Society for Technical Education (AP).\n' +
            '- **IIC Rating**: The Institutional Innovation Council (IIC) at MITS holds the **highest 4-star rating**.\n' +
            '- **NPTEL**: Ranked among the **top 20 institutions** nationally with an **AAA rating**.'
    },
    {
        keywords: ['faculty', 'hod', 'head', 'department head', 'teachers', 'professor', 'staff', 'teach', 'padma', 'sundaramurthy', 'priya', 'sandhya', 'praveen', 'udayakumar', 'geethanjali', 'sivaraman', 'tharakeswara'],
        response: 'The Department of **Computer Science & Engineering (Artificial Intelligence and Machine Learning)** and **Computer Science & Engineering (Networks)** is led by a distinguished faculty cohort:\n\n' +
            '- **Dr. S. Padma** (Assoc. Professor & Head of Department): Ph.D. from Bharathiar University.\n' +
            '- **Dr. Sundaramurthy Pandurangan** (Professor of Practice): Ph.D. from IIT Roorkee.\n' +
            '- **Dr. S. Priya** (Sr. Asst. Professor): Ph.D. from Anna University.\n' +
            '- **Dr. Sandhya. E** (Asst. Professor): Ph.D. from SRMIST, Chennai.\n' +
            '- **Dr. R. Praveen Kumar** (Asst. Professor): Ph.D. from NIT Durgapur.\n' +
            '- **Mr. P. Udayakumar** (Asst. Professor): M.E., (Ph.D. candidate at VIT Vellore).\n' +
            '- **Mrs. N. Geethanjali** (Asst. Professor): M.Tech., (Ph.D. candidate at Mohan Babu University).\n' +
            '- **Mr. V. Sivaraman** (Asst. Professor): M.E., (Ph.D. candidate at Visvesvaraya Technological University).\n' +
            '- **Mr. Tharakeswara Raju B** (Asst. Professor): M.Tech., (Ph.D. candidate at IIT Tirupati).\n' +
            '- **Mr. G. Nithin** (Asst. Professor): MS.\n' +
            '- **Mrs. D. Bhargavajyothi** (Asst. Professor): M.Tech.\n\n' +
            'Would you like detail on a specific faculty member or their academic research background?'
    },
    {
        keywords: ['syllabus', 'curriculum', 'subjects', 'courses', 'r23', 'semester', 'course structure', 'study', 'classes', 'b.tech', 'btech'],
        response: 'MITS offers a flexible, modern, industry-aligned B.Tech curriculum. Here is the structure for the CSE (AI & ML) and CSE (Networks) departments:\n\n' +
            '**CSE - (AI & ML) Curriculum Highlights:**\n' +
            '- **1st Year I Sem**: Basic Electrical & Electronics Engineering, EEE Workshop, Computer Programming Lab, NSS/NCC/Scouts.\n' +
            '- **1st Year II Sem**: Differential Equations & Vector Calculus, Basic Civil & Mechanical Engineering, Communicative English Lab, Health & Wellness.\n' +
            '- **2nd Year I Sem**: Economics and Financial Accounting for Engineers, Probability and Statistics for CS, Digital Logic & Computer Organization, DBMS Laboratory.\n' +
            '- **2nd Year II Sem**: Discrete Mathematical Structures, Innovation & Incubation, Principles of AI, Advanced Data Structures & Algorithms, AI & ML Lab.\n\n' +
            '**CSE - (Networks) Curriculum Highlights (2nd Year):**\n' +
            '- **2nd Year I Sem**: OOPs through Java, Java Lab, Digital Logic & Computer Organization, DBMS, Probability & Stats.\n' +
            '- **2nd Year II Sem**: Discrete Math, Data Communications & Computer Networks, Automata Theory & Compiler Design, Advanced Data Structures.'
    },
    {
        keywords: ['mou', 'collaboration', 'partnership', 'agreement', 'international', 'japan', 'aizu', 'bgsu', 'industry', 'exchange', 'companies'],
        response: 'MITS is globally connected and has signed multiple milestone MoUs for academic and training programs:\n' +
            '- **University of Aizu, Japan**: Prestigious MoU for academic collaborations. **7 final-year B.Tech students** were recently selected for international internships at Aizu, Japan!\n' +
            '- **QNX Pi Square Technologies**: Signed to train students in Embedded Systems and Automotive Software.\n' +
            '- **Bowling Green State University (BGSU), USA**: MoU signed for academic exchange.\n' +
            '- **Xenovex Technologies, Chennai**: MoU with the CSE (AI & ML) department for internships.\n' +
            '- **Menmozhi Technologies, Trichy**: MoU signed in Dec 2024 for technical training and industry bootcamps.\n' +
            '- **Grats Technologies**: Partnered with the Computer Applications department.'
    },
    {
        keywords: ['events', 'event', 'hackathon', 'symposium', 'workshop', 'seminar', 'webinar', 'talk', 'singularity', 'summit', 'aimax', 'invicta', 'cyber', 'hacking'],
        response: 'MITS has hosted several high-impact academic and technical events recently:\n' +
            '- **Internal Hackathon 2025**: Organized on Sept 16, 2025 by CSE (AI & ML).\n' +
            '- **AIMAX-2K25**: A One-Day National Level Technical Symposium by the Department of CSE (AI & ML).\n' +
            '- **INVICTA-2K25**: A Technical Symposium organized by the Computer Science and Technology Department.\n' +
            '- **Agentic AI Workshop**: One-day hands-on workshop on "Beginner\'s Guide to Agentic AI: Creating Intentional AI" (August 22, 2025).\n' +
            '- **Singularity India Summit**: Students and faculty attended this summit in Bangalore on August 29-30, 2025.\n' +
            '- **FDP on Computing**: Faculty Development Programme on "Future of Computing – Artificial Intelligence, Quantum, and Beyond".\n' +
            '- **Cybersecurity Guest Lecture**: "Live Hacking in Action: Cyber Threats and Real-World Exploits" by CSE Cyber Security.'
    },
    {
        keywords: ['club', 'clubs', 'ncc', 'nss', 'drone', 'coding', 'student activities', 'sac', 'sports', 'fest', 'ashv'],
        response: 'MITS features active student clubs, NCC, and NSS chapters:\n' +
            '- **NCC**: Recognized as the **Best NCC Unit (Senior Division/Senior Wing)** in Andhra Pradesh! Cadets achieved 100% results in their B and C Certificate Exams (2024-25).\n' +
            '- **Drone Technology Club**: Promotes innovation, flight mechanics, and assembly skills in drone tech.\n' +
            '- **Coding Club**: Launched under the Student Activity Center (SAC) to boost programming excellence.\n' +
            '- **Ashv 2025**: A National-Level Techno-Cultural-Sports Fest celebrated with grand sports tournaments and cultural programs.\n' +
            '- **Film & Cultural Club**: Organized "Cinema Craft-2K25".'
    },
    {
        keywords: ['placement', 'placements', 'jobs', 'recruit', 'salary', 'career', 'hr connect', 'training', 'aptitude', 'skills'],
        response: 'MITS has a robust placement training program beginning in the second year, ensuring students are industry-ready:\n' +
            '- **Aptitude & Soft Skills**: Continuous training starts in B.Tech II year, covering quantitative aptitude, verbal ability, and mock interviews.\n' +
            '- **HR Connect 2K25**: Themed "Careers for Tomorrow", bridging industry leaders with students.\n' +
            '- **Career Guidance Program**: Two-day event on "Engineering Elevates and Enlightens" hosted by CSE (AI & ML) on September 9-10, 2025.\n' +
            '- **IT & Core Sectors**: Graduates are placed in top tier software enterprises, MNCs, and electronics companies.'
    },
    {
        keywords: ['address', 'contact', 'location', 'phone', 'email', 'map', 'where is', 'locate', 'angallu', 'madanapalle', 'pincode', 'call'],
        response: 'Here are the contact and location details for MITS:\n' +
            '- **Campus Address**: Madanapalle Institute of Technology & Science, Kadiri Road, Angallu, Madanapalle - 517325, Chittoor District, Andhra Pradesh, India.\n' +
            '- **Campus Size**: 26.17 acres located on NH-205, approximately 10 km from Madanapalle town.\n' +
            '- **Phone Number**: +91-9154291788, 08571-280255, 08571-280706\n' +
            '- **Founder Academy**: Ratakonda Ranga Reddy Educational Academy (established 1998).'
    },
    {
        keywords: ['history', 'about mits', 'tell me about mits', 'university background', 'vision', 'mission', 'chancellor', 'establish'],
        response: 'MITS was established in **1998** in Madanapalle, Andhra Pradesh, under the Ratakonda Ranga Reddy Educational Academy. Here are the core details:\n' +
            '- **Chancellor & Founder**: **Dr. N. Vijaya Bhaskar Choudary**.\n' +
            '- **Co-founder**: Late Sri N. Krishna Kumar.\n' +
            '- **Academic Heritage**: Celebrating 27 years of academic excellence.\n' +
            '- **Vision**: To serve the region, nation, and world through academic excellence, research relevance, and community engagement.\n' +
            '- **Mission**: Foster analytical thinking, strengthen industry partnerships, and develop ethical solutions for socio-economic progress.'
    }
];

// Contextual fallback response when keyword scores are low
const FALLBACK_RESPONSES = [
    "I'm here to assist you with queries related to **MITS University**! You can ask me about:\n- Department details or faculty (e.g., 'Who is the head of AI/ML?')\n- University ranking and NAAC grade\n- The R23 syllabus / course curriculum\n- Recent workshops, hackathons, and MoUs\n- Contact details and campus location\n\nCould you try rephrasing your question?",
    "That is interesting, but I don't have that specific record in my MITS database. Ask me about MITS course subjects, AI/ML professors, placement stats, or student clubs!",
    "I specialize in MITS academic and campus queries. For security and accuracy, I limit answers to verified university data. Can I help you find information about the AI/ML HOD, B.Tech curriculum, or international MoUs like Japan's University of Aizu?"
];

let fallbackIndex = 0;

// Search function (Basic keyword count matching / similarity score)
function searchKnowledgeBase(query) {
    const cleanedQuery = query.toLowerCase().replace(/[^\w\s]/g, ' ');
    const queryWords = cleanedQuery.split(/\s+/).filter(w => w.length > 2);

    if (queryWords.length === 0) {
        return "Please ask a complete question! I'm ready to tell you about MITS.";
    }

    let bestMatch = null;
    let maxMatches = 0;

    // Search through the pre-compiled knowledge base
    KNOWLEDGE_BASE.forEach(entry => {
        let matchScore = 0;
        
        // Count matches
        entry.keywords.forEach(keyword => {
            if (cleanedQuery.includes(keyword)) {
                matchScore += 2; // Exact keyword match is weighted higher
            }
            
            // Check word parts
            queryWords.forEach(word => {
                if (word.startsWith(keyword) || keyword.startsWith(word)) {
                    matchScore += 0.5;
                }
            });
        });

        if (matchScore > maxMatches) {
            maxMatches = matchScore;
            bestMatch = entry;
        }
    });

    // Threshold score check
    if (maxMatches >= 1.5 && bestMatch) {
        return bestMatch.response;
    }

    // Get a fallback response and cycle through them
    const response = FALLBACK_RESPONSES[fallbackIndex];
    fallbackIndex = (fallbackIndex + 1) % FALLBACK_RESPONSES.length;
    return response;
}
