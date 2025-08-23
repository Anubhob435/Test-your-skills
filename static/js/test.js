/**
 * Test Interface JavaScript
 * Handles test taking functionality, timer, navigation, and submission
 */

class TestInterface {
    constructor() {
        this.testData = window.testData || {};
        this.questions = [];
        this.currentQuestionIndex = 0;
        this.answers = {};
        this.markedForReview = new Set();
        this.visitedQuestions = new Set();
        this.timer = null;
        this.timeRemaining = this.testData.timeLimit || 3600; // Default 1 hour
        this.autoSubmitWarningShown = false;
        this.testStartTime = new Date();
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadTestQuestions();
        this.startTimer();
    }
    
    bindEvents() {
        // Navigation buttons
        document.getElementById('prev-btn')?.addEventListener('click', () => {
            this.navigateToQuestion(this.currentQuestionIndex - 1);
        });
        
        document.getElementById('next-btn')?.addEventListener('click', () => {
            this.navigateToQuestion(this.currentQuestionIndex + 1);
        });
        
        // Answer management
        document.getElementById('clear-answer-btn')?.addEventListener('click', () => {
            this.clearCurrentAnswer();
        });
        
        document.getElementById('mark-review-btn')?.addEventListener('click', () => {
            this.toggleMarkForReview();
        });
        
        // Submit test
        document.getElementById('submit-test-btn')?.addEventListener('click', () => {
            this.showSubmitModal();
        });
        
        // Modal events
        document.getElementById('close-submit-modal')?.addEventListener('click', () => {
            this.hideSubmitModal();
        });
        
        document.getElementById('cancel-submit')?.addEventListener('click', () => {
            this.hideSubmitModal();
        });
        
        document.getElementById('confirm-submit')?.addEventListener('click', () => {
            this.submitTest();
        });
        
        document.getElementById('submit-now-btn')?.addEventListener('click', () => {
            this.submitTest();
        });
        
        // Retry button
        document.getElementById('retry-load-btn')?.addEventListener('click', () => {
            this.loadTestQuestions();
        });
        
        // Prevent accidental page refresh
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges()) {
                e.preventDefault();
                e.returnValue = 'You have an active test. Are you sure you want to leave?';
                return e.returnValue;
            }
        });
        
        // Auto-save answers periodically
        setInterval(() => {
            this.autoSaveProgress();
        }, 30000); // Save every 30 seconds
    }
    
    async loadTestQuestions() {
        try {
            this.showLoading();
            
            const response = await API.get(`/api/tests/${this.testData.testId}`);
            
            if (response.sections && response.sections.length > 0) {
                // Flatten questions from sections into a single array
                this.questions = [];
                response.sections.forEach(section => {
                    if (section.questions && section.questions.length > 0) {
                        section.questions.forEach(question => {
                            question.section_name = section.section_name;
                            this.questions.push(question);
                        });
                    }
                });
                
                if (this.questions.length > 0) {
                    this.processQuestions();
                    this.renderQuestionNavigation();
                    this.navigateToQuestion(0);
                    this.showContent();
                } else {
                    throw new Error('No questions found in sections');
                }
            } else {
                throw new Error('No sections received');
            }
            
        } catch (error) {
            console.error('Error loading test questions:', error);
            this.showError();
            UI.showError('Failed to load test questions. Please try again.');
        }
    }
    
    processQuestions() {
        // Group questions by section and add metadata
        let questionIndex = 0;
        this.questions.forEach((question, index) => {
            question.globalIndex = index;
            question.visited = false;
            question.answered = false;
            question.markedForReview = false;
        });
        
        // Initialize answers object
        this.answers = {};
        this.questions.forEach(q => {
            this.answers[q.id] = null;
        });
    }
    
    renderQuestionNavigation() {
        const navGrid = document.getElementById('question-nav-grid');
        if (!navGrid) return;
        
        navGrid.innerHTML = this.questions.map((question, index) => `
            <button class="question-nav-btn w-8 h-8 text-sm font-medium border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                    data-question-index="${index}"
                    onclick="testInterface.navigateToQuestion(${index})">
                ${index + 1}
            </button>
        `).join('');
    }
    
    navigateToQuestion(index) {
        if (index < 0 || index >= this.questions.length) return;
        
        // Save current answer if any
        this.saveCurrentAnswer();
        
        // Update current question
        this.currentQuestionIndex = index;
        this.visitedQuestions.add(index);
        
        // Render question
        this.renderCurrentQuestion();
        this.updateNavigationState();
        this.updateProgress();
    }
    
    renderCurrentQuestion() {
        const question = this.questions[this.currentQuestionIndex];
        if (!question) return;
        
        // Update question info
        document.getElementById('current-question-num').textContent = this.currentQuestionIndex + 1;
        document.getElementById('question-number').textContent = this.currentQuestionIndex + 1;
        document.getElementById('current-section').textContent = question.section_name || question.section || 'General';
        
        // Update section header
        const sectionTitle = document.getElementById('section-title');
        const sectionInfo = document.getElementById('section-info');
        if (sectionTitle) sectionTitle.textContent = question.section_name || question.section || 'General Questions';
        if (sectionInfo) sectionInfo.textContent = `Question ${this.currentQuestionIndex + 1} of ${this.questions.length}`;
        
        // Update difficulty
        const difficultyEl = document.getElementById('question-difficulty');
        if (difficultyEl) {
            difficultyEl.textContent = question.difficulty || 'Medium';
            difficultyEl.className = `px-3 py-1 text-xs font-medium rounded-full ${this.getDifficultyClass(question.difficulty)}`;
        }
        
        // Update question text
        document.getElementById('question-text').innerHTML = question.question_text || question.question;
        
        // Render options
        this.renderQuestionOptions(question);
        
        // Update mark for review button
        const markBtn = document.getElementById('mark-review-btn');
        if (markBtn) {
            if (this.markedForReview.has(this.currentQuestionIndex)) {
                markBtn.textContent = 'Unmark Review';
                markBtn.className = 'px-4 py-2 border border-yellow-400 bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200 transition-colors';
            } else {
                markBtn.textContent = 'Mark for Review';
                markBtn.className = 'px-4 py-2 border border-yellow-400 text-yellow-700 rounded-lg hover:bg-yellow-50 transition-colors';
            }
        }
    }
    
    renderQuestionOptions(question) {
        const container = document.getElementById('options-container');
        if (!container) return;
        
        const options = question.options || [];
        const currentAnswer = this.answers[question.id];
        
        container.innerHTML = options.map((option, index) => {
            const optionKey = String.fromCharCode(65 + index); // A, B, C, D
            const isSelected = currentAnswer === optionKey;
            
            return `
                <div class="option-button border-2 border-gray-200 rounded-lg p-4 ${isSelected ? 'selected' : ''}"
                     onclick="testInterface.selectOption('${optionKey}')">
                    <div class="flex items-center space-x-3">
                        <div class="flex-shrink-0">
                            <div class="w-6 h-6 border-2 border-gray-300 rounded-full flex items-center justify-center ${isSelected ? 'border-blue-600 bg-blue-600' : ''}">
                                ${isSelected ? '<div class="w-3 h-3 bg-white rounded-full"></div>' : ''}
                            </div>
                        </div>
                        <div class="flex-1">
                            <div class="flex items-center space-x-2">
                                <span class="font-medium text-gray-900">${optionKey}.</span>
                                <span class="text-gray-800">${option}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    selectOption(optionKey) {
        const question = this.questions[this.currentQuestionIndex];
        if (!question) return;
        
        // Update answer
        this.answers[question.id] = optionKey;
        
        // Re-render options to show selection
        this.renderQuestionOptions(question);
        
        // Update navigation state
        this.updateNavigationState();
        this.updateProgress();
    }
    
    saveCurrentAnswer() {
        // Answer is saved immediately when selected, so this is mainly for cleanup
        const question = this.questions[this.currentQuestionIndex];
        if (question && this.answers[question.id]) {
            question.answered = true;
        }
    }
    
    clearCurrentAnswer() {
        const question = this.questions[this.currentQuestionIndex];
        if (!question) return;
        
        this.answers[question.id] = null;
        question.answered = false;
        
        this.renderQuestionOptions(question);
        this.updateNavigationState();
        this.updateProgress();
    }
    
    toggleMarkForReview() {
        if (this.markedForReview.has(this.currentQuestionIndex)) {
            this.markedForReview.delete(this.currentQuestionIndex);
        } else {
            this.markedForReview.add(this.currentQuestionIndex);
        }
        
        this.renderCurrentQuestion();
        this.updateNavigationState();
    }
    
    updateNavigationState() {
        // Update previous/next buttons
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        
        if (prevBtn) {
            prevBtn.disabled = this.currentQuestionIndex === 0;
        }
        
        if (nextBtn) {
            if (this.currentQuestionIndex === this.questions.length - 1) {
                nextBtn.textContent = 'Finish';
                nextBtn.onclick = () => this.showSubmitModal();
            } else {
                nextBtn.textContent = 'Next →';
                nextBtn.onclick = () => this.navigateToQuestion(this.currentQuestionIndex + 1);
            }
        }
        
        // Update question navigation grid
        const navButtons = document.querySelectorAll('.question-nav-btn');
        navButtons.forEach((btn, index) => {
            btn.className = 'question-nav-btn w-8 h-8 text-sm font-medium border border-gray-300 rounded transition-colors';
            
            if (index === this.currentQuestionIndex) {
                btn.classList.add('current');
            } else if (this.answers[this.questions[index].id]) {
                btn.classList.add('answered');
            } else if (this.markedForReview.has(index)) {
                btn.classList.add('bg-yellow-500', 'text-white', 'border-yellow-500');
            } else if (this.visitedQuestions.has(index)) {
                btn.classList.add('bg-gray-100', 'border-gray-400');
            }
        });
    }
    
    updateProgress() {
        const answeredCount = Object.values(this.answers).filter(answer => answer !== null).length;
        const progressPercentage = (answeredCount / this.questions.length) * 100;
        
        document.getElementById('progress-bar').style.width = `${progressPercentage}%`;
        document.getElementById('progress-text').textContent = `${Math.round(progressPercentage)}%`;
    }
    
    startTimer() {
        this.updateTimerDisplay();
        
        this.timer = setInterval(() => {
            this.timeRemaining--;
            this.updateTimerDisplay();
            
            // Show warning at 5 minutes
            if (this.timeRemaining === 300 && !this.autoSubmitWarningShown) {
                this.showAutoSubmitWarning();
            }
            
            // Auto-submit when time runs out
            if (this.timeRemaining <= 0) {
                this.autoSubmitTest();
            }
        }, 1000);
    }
    
    updateTimerDisplay() {
        const hours = Math.floor(this.timeRemaining / 3600);
        const minutes = Math.floor((this.timeRemaining % 3600) / 60);
        const seconds = this.timeRemaining % 60;
        
        let timeText;
        if (hours > 0) {
            timeText = `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        } else {
            timeText = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
        
        const timerEl = document.getElementById('timer-text');
        const timerDisplay = document.getElementById('timer-display');
        
        if (timerEl) timerEl.textContent = timeText;
        
        // Add warning styling when time is low
        if (timerDisplay) {
            if (this.timeRemaining <= 300) { // 5 minutes
                timerDisplay.classList.add('timer-warning', 'bg-red-100', 'text-red-700');
            } else if (this.timeRemaining <= 600) { // 10 minutes
                timerDisplay.classList.add('bg-yellow-100', 'text-yellow-700');
            }
        }
    }
    
    showAutoSubmitWarning() {
        this.autoSubmitWarningShown = true;
        const modal = document.getElementById('auto-submit-warning');
        if (!modal) return;
        
        modal.classList.remove('hidden');
        
        // Countdown in the warning
        let warningTime = 60;
        const countdownEl = document.getElementById('warning-countdown');
        
        const warningTimer = setInterval(() => {
            warningTime--;
            if (countdownEl) countdownEl.textContent = warningTime;
            
            if (warningTime <= 0) {
                clearInterval(warningTimer);
                modal.classList.add('hidden');
            }
        }, 1000);
        
        // Hide warning after 60 seconds
        setTimeout(() => {
            modal.classList.add('hidden');
            clearInterval(warningTimer);
        }, 60000);
    }
    
    showSubmitModal() {
        const modal = document.getElementById('submit-modal');
        if (!modal) return;
        
        // Update modal statistics
        const answeredCount = Object.values(this.answers).filter(answer => answer !== null).length;
        const remainingCount = this.questions.length - answeredCount;
        const reviewCount = this.markedForReview.size;
        
        document.getElementById('modal-answered-count').textContent = answeredCount;
        document.getElementById('modal-remaining-count').textContent = remainingCount;
        document.getElementById('modal-review-count').textContent = reviewCount;
        
        // Update time left
        const hours = Math.floor(this.timeRemaining / 3600);
        const minutes = Math.floor((this.timeRemaining % 3600) / 60);
        const timeLeft = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
        document.getElementById('modal-time-left').textContent = timeLeft;
        
        modal.classList.remove('hidden');
    }
    
    hideSubmitModal() {
        const modal = document.getElementById('submit-modal');
        if (modal) modal.classList.add('hidden');
    }
    
    async submitTest() {
        try {
            this.hideSubmitModal();
            
            // Stop timer
            if (this.timer) {
                clearInterval(this.timer);
                this.timer = null;
            }
            
            // Calculate time taken
            const timeTaken = Math.floor((new Date() - this.testStartTime) / 1000);
            
            // Prepare submission data
            const submissionData = {
                answers: this.answers,
                time_taken: timeTaken,
                started_at: this.testStartTime.toISOString(),
                marked_for_review: Array.from(this.markedForReview)
            };
            
            UI.showSuccess('Submitting your test...');
            
            // Submit to server
            const response = await API.post(`/api/tests/${this.testData.testId}/submit`, submissionData);
            
            if (response.attempt_id) {
                // Redirect to results page
                window.location.href = `/test/${this.testData.testId}/results/${response.attempt_id}`;
            } else {
                throw new Error('No attempt ID received');
            }
            
        } catch (error) {
            console.error('Error submitting test:', error);
            UI.showError('Failed to submit test. Please try again.');
            
            // Restart timer if submission failed
            if (!this.timer) {
                this.startTimer();
            }
        }
    }
    
    autoSubmitTest() {
        // Hide any open modals
        this.hideSubmitModal();
        document.getElementById('auto-submit-warning')?.classList.add('hidden');
        
        UI.showWarning('Time expired! Auto-submitting your test...');
        this.submitTest();
    }
    
    async autoSaveProgress() {
        try {
            // Save current progress to prevent data loss
            const progressData = {
                answers: this.answers,
                current_question: this.currentQuestionIndex,
                marked_for_review: Array.from(this.markedForReview),
                time_remaining: this.timeRemaining
            };
            
            // This would be a separate endpoint for auto-saving
            // await API.post(`/api/tests/${this.testData.testId}/save-progress`, progressData);
            
        } catch (error) {
            console.error('Error auto-saving progress:', error);
            // Don't show error to user for auto-save failures
        }
    }
    
    hasUnsavedChanges() {
        // Check if there are any answers that haven't been submitted
        return Object.values(this.answers).some(answer => answer !== null);
    }
    
    // Utility methods
    getDifficultyClass(difficulty) {
        switch (difficulty?.toLowerCase()) {
            case 'easy':
                return 'bg-green-100 text-green-700';
            case 'hard':
                return 'bg-red-100 text-red-700';
            default:
                return 'bg-gray-100 text-gray-700';
        }
    }
    
    showLoading() {
        document.getElementById('loading-state')?.classList.remove('hidden');
        document.getElementById('question-container')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
    }
    
    showContent() {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('question-container')?.classList.remove('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
    }
    
    showError() {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('question-container')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.remove('hidden');
    }
}

// Initialize test interface when DOM is loaded
let testInterface;
document.addEventListener('DOMContentLoaded', function() {
    testInterface = new TestInterface();
});

// Export for global access
window.testInterface = testInterface;