function shiftiApp() {
    return {
        // App state
        symptoms: '',
        currentLanguage: 'en',
        loading: false,
        showResults: false,
        showApp: false,
        results: null,
        error: '',
        isListening: false,
        recognition: null,

        // Initialize the app
        init() {
            this.setupSpeechRecognition();
            // Check if browser supports Arabic
            if (navigator.language.includes('ar')) {
                this.currentLanguage = 'ar';
                document.documentElement.dir = 'rtl';
            }
        },

        // Language toggle
        toggleLanguage() {
            this.currentLanguage = this.currentLanguage === 'en' ? 'ar' : 'en';
            document.documentElement.dir = this.currentLanguage === 'ar' ? 'rtl' : 'ltr';
            document.documentElement.lang = this.currentLanguage;
        },

        // Speech recognition setup
        setupSpeechRecognition() {
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                this.recognition = new SpeechRecognition();
                
                this.recognition.continuous = false;
                this.recognition.interimResults = false;
                this.recognition.lang = this.currentLanguage === 'ar' ? 'ar-AE' : 'en-US';
                
                this.recognition.onstart = () => {
                    this.isListening = true;
                };
                
                this.recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    this.symptoms = transcript;
                    this.isListening = false;
                };
                
                this.recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    this.isListening = false;
                    this.error = this.currentLanguage === 'en' 
                        ? 'Voice input failed. Please try typing instead.' 
                        : 'فشل الإدخال الصوتي. يرجى المحاولة بالكتابة.';
                };
                
                this.recognition.onend = () => {
                    this.isListening = false;
                };
            }
        },

        // Toggle voice input
        toggleVoiceInput() {
            if (!this.recognition) {
                this.error = this.currentLanguage === 'en' 
                    ? 'Voice input not supported on this browser' 
                    : 'الإدخال الصوتي غير مدعوم في هذا المتصفح';
                return;
            }

            if (this.isListening) {
                this.recognition.stop();
            } else {
                this.error = '';
                this.recognition.lang = this.currentLanguage === 'ar' ? 'ar-AE' : 'en-US';
                this.recognition.start();
            }
        },

        // Find clinics using AI
        async findClinics() {
            if (!this.symptoms.trim()) {
                this.error = this.currentLanguage === 'en' 
                    ? 'Please describe your symptoms' 
                    : 'يرجى وصف الأعراض';
                return;
            }

            this.loading = true;
            this.error = '';

            try {
                const response = await fetch('/triage', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        symptoms: this.symptoms,
                        language: this.currentLanguage
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                this.results = data;
                this.showResults = true;

                // Play notification sound for urgent cases
                if (data.urgency_level === 'emergency') {
                    this.playNotificationSound();
                }

            } catch (error) {
                console.error('Triage request failed:', error);
                this.error = this.currentLanguage === 'en' 
                    ? `Failed to analyze symptoms: ${error.message}` 
                    : `فشل في تحليل الأعراض: ${error.message}`;
            } finally {
                this.loading = false;
            }
        },

        // Reset search
        resetSearch() {
            this.symptoms = '';
            this.showResults = false;
            this.results = null;
            this.error = '';
        },

        // Call clinic
        callClinic(phone) {
            window.location.href = `tel:${phone}`;
        },

        // Share via WhatsApp
        shareWhatsApp(message) {
            const encodedMessage = encodeURIComponent(message);
            const whatsappUrl = `https://wa.me/?text=${encodedMessage}`;
            window.open(whatsappUrl, '_blank');
        },

        // Play notification sound for urgent cases
        playNotificationSound() {
            try {
                // Create a simple beep sound using Web Audio API
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();

                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);

                oscillator.frequency.value = 800;
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
            } catch (error) {
                console.log('Audio notification not available');
            }
        },

        // Format urgency level for display
        formatUrgency(level) {
            const urgencyMap = {
                'en': {
                    'low': 'Low Priority',
                    'moderate': 'Moderate',
                    'high': 'High Priority', 
                    'emergency': 'EMERGENCY'
                },
                'ar': {
                    'low': 'أولوية منخفضة',
                    'moderate': 'معتدل',
                    'high': 'أولوية عالية',
                    'emergency': 'طارئ'
                }
            };
            
            return urgencyMap[this.currentLanguage][level] || level;
        },

        // Get urgency color class
        getUrgencyColorClass(level) {
            const colorMap = {
                'low': 'bg-green-100 text-green-800',
                'moderate': 'bg-yellow-100 text-yellow-800',
                'high': 'bg-orange-100 text-orange-800',
                'emergency': 'bg-red-100 text-red-800'
            };
            return colorMap[level] || 'bg-gray-100 text-gray-800';
        }
    }
}

// Service worker removed to avoid 404 errors

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

// Handle online/offline status
window.addEventListener('online', () => {
    console.log('App is online');
});

window.addEventListener('offline', () => {
    console.log('App is offline');
});
