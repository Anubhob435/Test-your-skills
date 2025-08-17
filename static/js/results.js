/**
 * Test Results JavaScript
 * Handles results display, question review, and analysis
 */

class TestResults {
    constructor() {
        this.resultsData = window.resultsData || {};
        this.questions = [];
        this.filteredQuestions = [];
        this.currentFilter = 'all';
        this.questionsPerPage = 10;
        this.currentPage = 1;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadResultsData();
    }
    
    bindEvents() {
        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setFilter(e.target.dataset.filter);
            });
        });
        
        // Load more questions
        document.getElementById('load-more-questions')?.addEventListener('click', () => {
            this.loadMoreQuestions();
        });
        
        // Download report
        document.getElementById('download-report-btn')?.addEventListener('click', () => {
            this.downloadReport();
        });
        
        // Modal events
        document.getElementById('close-question-modal')?.addEventListener('click', () => {
            this.closeQuestionModal();
        });
        
        document.getElementById('question-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'question-modal') {
                this.closeQuestionModal();
            }
        });
        
        // Retry button
        document.getElementById('retry-load-btn')?.addEventListener('click', () => {
            this.loadResultsData();
        });
    }
    
    async loadResultsData() {
        try {
            this.showLoading();
            
            // Load detailed results
            const response = await API.get(`/api/tests/${this.resultsData.testId}/results/${this.resultsData.attemptId}`);
            
            if (response.questions && response.statistics) {
                this.questions = response.questions;
                this.statistics = response.statistics;
                this.renderResults();
                this.showContent();
            } else {
                throw new Error('Invalid results data received');
            }
            
        } catch (error) {
            console.error('Error loading results:', error);
            this.showError();
            UI.showError('Failed to load test results. Please try again.');
        }
    }
    
    renderResults() {
        this.renderScoreOverview();
        this.renderSectionPerformance();
        this.renderComparison();
        this.renderQuestions();
        this.renderRecommendations();
        this.animateScoreCircle();
    }
    
    renderScoreOverview() {
        const { score, totalQuestions, timeTaken } = this.resultsData;
        const percentage = Math.round((score / totalQuestions) * 100);
        
        // Update score display
        document.getElementById('score-percentage').textContent = `${percentage}%`;
        document.getElementById('correct-count').textContent = score;
        document.getElementById('total-count').textContent = totalQuestions;
        document.getElementById('accuracy-rate').textContent = `${percentage}%`;
        
        // Format and display time taken
        const hours = Math.floor(timeTaken / 3600);
        const minutes = Math.floor((timeTaken % 3600) / 60);
        const timeText = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
        document.getElementById('time-taken').textContent = timeText;
        
        // Set performance badge
        const performanceBadge = document.getElementById('performance-badge');
        if (performanceBadge) {
            const { level, text } = this.getPerformanceLevel(percentage);
            performanceBadge.textContent = text;
            performanceBadge.className = `performance-badge performance-${level}`;
        }
    }
    
    renderSectionPerformance() {
        const container = document.getElementById('section-performance');
        if (!container || !this.statistics.section_performance) return;
        
        container.innerHTML = this.statistics.section_performance.map(section => {
            const percentage = Math.round((section.correct / section.total) * 100);
            return `
                <div class="space-y-2">
                    <div class="flex justify-between items-center">
                        <span class="text-sm font-medium text-gray-700">${section.section}</span>
                        <span class="text-sm text-gray-600">${section.correct}/${section.total}</span>
                    </div>
                    <div class="section-progress bg-gray-200">
                        <div class="h-full bg-blue-600 transition-all duration-1000" 
                             style="width: ${percentage}%"></div>
                    </div>
                    <div class="flex justify-between text-xs text-gray-500">
                        <span>${percentage}% accuracy</span>
                        <span class="capitalize">${this.getPerformanceLevel(percentage).level}</span>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    renderComparison() {
        if (!this.statistics.comparison) return;
        
        const { your_score, average_score, rank, total_attempts } = this.statistics.comparison;
        
        document.getElementById('comparison-your-score').textContent = `${your_score}%`;
        document.getElementById('comparison-average').textContent = `${average_score}%`;
        document.getElementById('comparison-rank').textContent = `${rank}/${total_attempts}`;
    }
    
    renderQuestions() {
        this.filteredQuestions = this.filterQuestions(this.currentFilter);
        this.currentPage = 1;
        this.renderQuestionsList();
    }
    
    filterQuestions(filter) {
        switch (filter) {
            case 'correct':
                return this.questions.filter(q => q.is_correct);
            case 'incorrect':
                return this.questions.filter(q => q.user_answer && !q.is_correct);
            case 'not-attempted':
                return this.questions.filter(q => !q.user_answer);
            default:
                return [...this.questions];
        }
    }
    
    renderQuestionsList() {
        const container = document.getElementById('questions-review');
        if (!container) return;
        
        const startIndex = 0;
        const endIndex = this.currentPage * this.questionsPerPage;
        const questionsToShow = this.filteredQuestions.slice(startIndex, endIndex);
        
        if (questionsToShow.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <p>No questions found for the selected filter.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = questionsToShow.map((question, index) => {
            const statusClass = this.getQuestionStatusClass(question);
            const statusIcon = this.getQuestionStatusIcon(question);
            
            return `
                <div class="question-review-card border-2 ${statusClass} rounded-lg p-6 animate-fade-in" 
                     style="animation-delay: ${index * 0.1}s">
                    <div class="flex items-start justify-between mb-4">
                        <div class="flex items-center space-x-3">
                            <div class="flex-shrink-0">
                                ${statusIcon}
                            </div>
                            <div>
                                <h3 class="font-semibold text-gray-900">Question ${question.question_number}</h3>
                                <p class="text-sm text-gray-600">${question.section} • ${question.difficulty}</p>
                            </div>
                        </div>
                        <button class="text-blue-600 hover:text-blue-800 text-sm font-medium"
                                onclick="testResults.showQuestionDetail(${question.id})">
                            View Details
                        </button>
                    </div>
                    
                    <div class="mb-4">
                        <p class="text-gray-800 leading-relaxed">${question.question_text}</p>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        ${question.options.map((option, optIndex) => {
                            const optionKey = String.fromCharCode(65 + optIndex);
                            const isUserAnswer = question.user_answer === optionKey;
                            const isCorrectAnswer = question.correct_answer === optionKey;
                            
                            let optionClass = 'border-gray-200 bg-gray-50';
                            if (isCorrectAnswer) {
                                optionClass = 'border-green-500 bg-green-50 text-green-800';
                            } else if (isUserAnswer && !isCorrectAnswer) {
                                optionClass = 'border-red-500 bg-red-50 text-red-800';
                            }
                            
                            return `
                                <div class="border-2 ${optionClass} rounded-lg p-3">
                                    <div class="flex items-center space-x-2">
                                        <span class="font-medium">${optionKey}.</span>
                                        <span>${option}</span>
                                        ${isCorrectAnswer ? '<span class="ml-auto text-green-600">✓</span>' : ''}
                                        ${isUserAnswer && !isCorrectAnswer ? '<span class="ml-auto text-red-600">✗</span>' : ''}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                    
                    ${question.explanation ? `
                        <div class="explanation-card p-4 rounded-lg">
                            <div class="flex items-center space-x-2 mb-2">
                                <svg class="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                                </svg>
                                <span class="font-medium text-blue-900">Explanation</span>
                            </div>
                            <p class="text-blue-800">${question.explanation}</p>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
        
        // Show/hide load more button
        const loadMoreBtn = document.getElementById('load-more-questions');
        if (loadMoreBtn) {
            if (endIndex < this.filteredQuestions.length) {
                loadMoreBtn.classList.remove('hidden');
            } else {
                loadMoreBtn.classList.add('hidden');
            }
        }
    }
    
    renderRecommendations() {
        const container = document.getElementById('recommendations-content');
        if (!container || !this.statistics.recommendations) return;
        
        container.innerHTML = this.statistics.recommendations.map(rec => `
            <div class="border border-gray-200 rounded-lg p-6">
                <div class="flex items-center space-x-3 mb-3">
                    <div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <svg class="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                        </svg>
                    </div>
                    <div>
                        <h3 class="font-semibold text-gray-900">${rec.title}</h3>
                        <p class="text-sm text-gray-600">${rec.category}</p>
                    </div>
                </div>
                <p class="text-gray-700 mb-4">${rec.description}</p>
                <div class="flex items-center justify-between">
                    <span class="text-sm text-gray-500">Priority: ${rec.priority}</span>
                    <button class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                        Learn More
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    setFilter(filter) {
        this.currentFilter = filter;
        
        // Update filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.filter === filter) {
                btn.classList.add('active');
            }
        });
        
        this.renderQuestions();
    }
    
    loadMoreQuestions() {
        this.currentPage++;
        this.renderQuestionsList();
    }
    
    showQuestionDetail(questionId) {
        const question = this.questions.find(q => q.id === questionId);
        if (!question) return;
        
        const modal = document.getElementById('question-modal');
        const title = document.getElementById('modal-question-title');
        const content = document.getElementById('modal-question-content');
        
        if (!modal || !title || !content) return;
        
        title.textContent = `Question ${question.question_number} - ${question.section}`;
        
        const statusClass = this.getQuestionStatusClass(question);
        const statusIcon = this.getQuestionStatusIcon(question);
        
        content.innerHTML = `
            <div class="space-y-6">
                <!-- Question Status -->
                <div class="flex items-center space-x-3 p-4 border-2 ${statusClass} rounded-lg">
                    ${statusIcon}
                    <div>
                        <p class="font-semibold">${this.getQuestionStatusText(question)}</p>
                        <p class="text-sm text-gray-600">${question.difficulty} • ${question.section}</p>
                    </div>
                </div>
                
                <!-- Question Text -->
                <div>
                    <h3 class="font-semibold text-gray-900 mb-3">Question</h3>
                    <p class="text-gray-800 leading-relaxed">${question.question_text}</p>
                </div>
                
                <!-- Options -->
                <div>
                    <h3 class="font-semibold text-gray-900 mb-3">Answer Options</h3>
                    <div class="space-y-3">
                        ${question.options.map((option, optIndex) => {
                            const optionKey = String.fromCharCode(65 + optIndex);
                            const isUserAnswer = question.user_answer === optionKey;
                            const isCorrectAnswer = question.correct_answer === optionKey;
                            
                            let optionClass = 'border-gray-200 bg-gray-50';
                            let statusText = '';
                            
                            if (isCorrectAnswer) {
                                optionClass = 'border-green-500 bg-green-50';
                                statusText = '<span class="text-green-600 font-medium ml-2">(Correct Answer)</span>';
                            } else if (isUserAnswer && !isCorrectAnswer) {
                                optionClass = 'border-red-500 bg-red-50';
                                statusText = '<span class="text-red-600 font-medium ml-2">(Your Answer)</span>';
                            }
                            
                            return `
                                <div class="border-2 ${optionClass} rounded-lg p-4">
                                    <div class="flex items-center">
                                        <span class="font-medium mr-3">${optionKey}.</span>
                                        <span class="flex-1">${option}</span>
                                        ${statusText}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
                
                <!-- Explanation -->
                ${question.explanation ? `
                    <div class="explanation-card p-6 rounded-lg">
                        <h3 class="font-semibold text-blue-900 mb-3 flex items-center">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                            </svg>
                            Explanation
                        </h3>
                        <p class="text-blue-800 leading-relaxed">${question.explanation}</p>
                    </div>
                ` : ''}
            </div>
        `;
        
        modal.classList.remove('hidden');
    }
    
    closeQuestionModal() {
        const modal = document.getElementById('question-modal');
        if (modal) modal.classList.add('hidden');
    }
    
    animateScoreCircle() {
        const { score, totalQuestions } = this.resultsData;
        const percentage = (score / totalQuestions) * 100;
        const circumference = 2 * Math.PI * 54; // radius = 54
        const offset = circumference - (percentage / 100) * circumference;
        
        const circle = document.getElementById('score-progress');
        if (circle) {
            // Animate the circle
            setTimeout(() => {
                circle.style.strokeDashoffset = offset;
                circle.style.transition = 'stroke-dashoffset 2s ease-in-out';
            }, 500);
        }
    }
    
    async downloadReport() {
        try {
            UI.showSuccess('Generating report...');
            
            // This would generate and download a PDF report
            const response = await API.get(`/api/tests/${this.resultsData.testId}/results/${this.resultsData.attemptId}/report`, {
                responseType: 'blob'
            });
            
            // Create download link
            const url = window.URL.createObjectURL(new Blob([response]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `test-report-${this.resultsData.company}-${new Date().toISOString().split('T')[0]}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            
            UI.showSuccess('Report downloaded successfully!');
            
        } catch (error) {
            console.error('Error downloading report:', error);
            UI.showError('Failed to download report. Please try again.');
        }
    }
    
    // Utility methods
    getPerformanceLevel(percentage) {
        if (percentage >= 90) return { level: 'excellent', text: 'Excellent' };
        if (percentage >= 75) return { level: 'good', text: 'Good' };
        if (percentage >= 60) return { level: 'average', text: 'Average' };
        return { level: 'poor', text: 'Needs Improvement' };
    }
    
    getQuestionStatusClass(question) {
        if (!question.user_answer) return 'not-attempted';
        return question.is_correct ? 'correct-answer' : 'incorrect-answer';
    }
    
    getQuestionStatusIcon(question) {
        if (!question.user_answer) {
            return `
                <div class="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                    <span class="text-gray-600 text-sm">?</span>
                </div>
            `;
        }
        
        if (question.is_correct) {
            return `
                <div class="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                    <svg class="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                    </svg>
                </div>
            `;
        }
        
        return `
            <div class="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                <svg class="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                </svg>
            </div>
        `;
    }
    
    getQuestionStatusText(question) {
        if (!question.user_answer) return 'Not Attempted';
        return question.is_correct ? 'Correct Answer' : 'Incorrect Answer';
    }
    
    showLoading() {
        document.getElementById('loading-state')?.classList.remove('hidden');
        document.getElementById('results-content')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
    }
    
    showContent() {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('results-content')?.classList.remove('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
    }
    
    showError() {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('results-content')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.remove('hidden');
    }
}

// Initialize results when DOM is loaded
let testResults;
document.addEventListener('DOMContentLoaded', function() {
    testResults = new TestResults();
});

// Export for global access
window.testResults = testResults;