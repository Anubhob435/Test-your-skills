/**
 * Test History JavaScript functionality
 * Handles test history loading, filtering, and pagination
 */

class TestHistory {
    constructor() {
        this.currentPage = 1;
        this.perPage = 10;
        this.filters = {
            company: '',
            date_from: '',
            date_to: ''
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadTestHistory();
    }
    
    bindEvents() {
        // Apply filters button
        document.getElementById('apply-filters')?.addEventListener('click', () => {
            this.applyFilters();
        });
        
        // Retry button
        document.getElementById('retry-load')?.addEventListener('click', () => {
            this.loadTestHistory();
        });
    }
    
    async loadTestHistory() {
        try {
            this.showLoading();
            
            // Build query parameters
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage,
                ...this.filters
            });
            
            // Remove empty filters
            for (let [key, value] of params.entries()) {
                if (!value) {
                    params.delete(key);
                }
            }
            
            const response = await API.get(`/api/test-history?${params.toString()}`);
            
            if (response.attempts && response.attempts.length > 0) {
                this.renderTestHistory(response);
                this.showContent();
            } else {
                this.showEmpty();
            }
            
        } catch (error) {
            console.error('Error loading test history:', error);
            this.showError();
            UI.showError('Failed to load test history. Please try again.');
        }
    }
    
    renderTestHistory(data) {
        const { attempts, pagination, summary } = data;
        
        // Render summary stats
        this.renderSummaryStats(summary);
        
        // Render test attempts
        this.renderTestAttempts(attempts);
        
        // Render pagination
        this.renderPagination(pagination);
    }
    
    renderSummaryStats(summary) {
        const container = document.getElementById('summary-stats');
        if (!container) return;
        
        container.innerHTML = `
            <div class="bg-white p-6 rounded-lg shadow-md border-l-4 border-blue-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Total Attempts</p>
                        <p class="text-2xl font-bold text-gray-900">${summary.total_attempts}</p>
                    </div>
                    <div class="text-blue-500">
                        <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                    </div>
                </div>
            </div>
            
            <div class="bg-white p-6 rounded-lg shadow-md border-l-4 border-green-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Average Score</p>
                        <p class="text-2xl font-bold text-gray-900">${summary.average_score}%</p>
                    </div>
                    <div class="text-green-500">
                        <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                </div>
            </div>
            
            <div class="bg-white p-6 rounded-lg shadow-md border-l-4 border-purple-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Companies</p>
                        <p class="text-2xl font-bold text-gray-900">${summary.companies_count}</p>
                    </div>
                    <div class="text-purple-500">
                        <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4zm0 2h12v8H4V6z"></path>
                        </svg>
                    </div>
                </div>
            </div>
            
            <div class="bg-white p-6 rounded-lg shadow-md border-l-4 border-orange-500">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Best Performance</p>
                        <p class="text-lg font-bold text-gray-900">${summary.best_performance ? summary.best_performance.company : 'N/A'}</p>
                        <p class="text-sm text-gray-600">${summary.best_performance ? summary.best_performance.percentage + '%' : ''}</p>
                    </div>
                    <div class="text-orange-500">
                        <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                        </svg>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderTestAttempts(attempts) {
        const container = document.getElementById('test-attempts');
        if (!container) return;
        
        container.innerHTML = attempts.map(attempt => `
            <div class="history-card p-6">
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <div class="flex items-center space-x-4">
                            <div>
                                <h3 class="text-lg font-semibold text-gray-900">${attempt.company}</h3>
                                <p class="text-sm text-gray-600">${this.formatDate(attempt.completed_at)}</p>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold ${this.getScoreColor(attempt.percentage)}">${attempt.percentage}%</div>
                                <div class="text-sm text-gray-600">${attempt.score}/${attempt.total_questions}</div>
                            </div>
                        </div>
                        
                        ${attempt.section_scores ? `
                            <div class="mt-4 grid grid-cols-2 md:grid-cols-3 gap-4">
                                ${Object.entries(attempt.section_scores).map(([section, scores]) => `
                                    <div class="text-center p-2 bg-gray-50 rounded">
                                        <div class="text-sm font-medium text-gray-700">${section}</div>
                                        <div class="text-lg font-semibold ${this.getScoreColor(scores.percentage)}">${scores.percentage}%</div>
                                        <div class="text-xs text-gray-600">${scores.score}/${scores.total}</div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="ml-6 flex flex-col space-y-2">
                        <button onclick="testHistory.viewResults(${attempt.test_id}, ${attempt.attempt_id})" 
                                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                            View Results
                        </button>
                        <button onclick="testHistory.retakeTest('${attempt.company}')" 
                                class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm">
                            Retake Test
                        </button>
                    </div>
                </div>
                
                ${attempt.time_taken ? `
                    <div class="mt-4 text-sm text-gray-600">
                        Time taken: ${this.formatTime(attempt.time_taken)}
                    </div>
                ` : ''}
            </div>
        `).join('');
    }
    
    renderPagination(pagination) {
        const container = document.getElementById('pagination');
        if (!container) return;
        
        if (pagination.pages <= 1) {
            container.innerHTML = '';
            return;
        }
        
        const prevDisabled = !pagination.has_prev;
        const nextDisabled = !pagination.has_next;
        
        container.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="text-sm text-gray-600">
                    Showing ${((pagination.page - 1) * pagination.per_page) + 1} to ${Math.min(pagination.page * pagination.per_page, pagination.total)} of ${pagination.total} results
                </div>
                
                <div class="flex space-x-2">
                    <button onclick="testHistory.goToPage(${pagination.page - 1})" 
                            ${prevDisabled ? 'disabled' : ''} 
                            class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors ${prevDisabled ? 'opacity-50 cursor-not-allowed' : ''}">
                        Previous
                    </button>
                    
                    <span class="px-3 py-2 bg-blue-600 text-white rounded-lg">
                        ${pagination.page} of ${pagination.pages}
                    </span>
                    
                    <button onclick="testHistory.goToPage(${pagination.page + 1})" 
                            ${nextDisabled ? 'disabled' : ''} 
                            class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors ${nextDisabled ? 'opacity-50 cursor-not-allowed' : ''}">
                        Next
                    </button>
                </div>
            </div>
        `;
    }
    
    applyFilters() {
        this.filters.company = document.getElementById('company-filter')?.value || '';
        this.filters.date_from = document.getElementById('date-from')?.value || '';
        this.filters.date_to = document.getElementById('date-to')?.value || '';
        
        this.currentPage = 1;
        this.loadTestHistory();
    }
    
    goToPage(page) {
        this.currentPage = page;
        this.loadTestHistory();
    }
    
    viewResults(testId, attemptId) {
        window.location.href = `/test/${testId}/results/${attemptId}`;
    }
    
    retakeTest(companyName) {
        window.location.href = `/dashboard?company=${encodeURIComponent(companyName)}`;
    }
    
    // Utility methods
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }
    
    formatTime(seconds) {
        if (!seconds) return 'Unknown';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = seconds % 60;
        
        if (hours > 0) {
            return `${hours}h ${minutes}m ${remainingSeconds}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            return `${remainingSeconds}s`;
        }
    }
    
    getScoreColor(score) {
        if (score >= 80) return 'text-green-600';
        if (score >= 60) return 'text-yellow-600';
        return 'text-red-600';
    }
    
    showLoading() {
        document.getElementById('loading-state')?.classList.remove('hidden');
        document.getElementById('history-content')?.classList.add('hidden');
        document.getElementById('empty-state')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
    }
    
    showContent() {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('history-content')?.classList.remove('hidden');
        document.getElementById('empty-state')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
    }
    
    showEmpty() {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('history-content')?.classList.add('hidden');
        document.getElementById('empty-state')?.classList.remove('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
    }
    
    showError() {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('history-content')?.classList.add('hidden');
        document.getElementById('empty-state')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.remove('hidden');
    }
}

// Initialize test history when DOM is loaded
let testHistory;
document.addEventListener('DOMContentLoaded', function() {
    testHistory = new TestHistory();
});

// Export for global access
window.testHistory = testHistory;