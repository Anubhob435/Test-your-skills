/**
 * Dashboard JavaScript functionality
 * Handles dashboard data loading, company selection, and user interactions
 */

class Dashboard {
    constructor() {
        this.dashboardData = null;
        this.companies = [];
        this.filteredCompanies = [];
        this.currentPage = 1;
        this.companiesPerPage = 6;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadDashboardData();
    }
    
    bindEvents() {
        // Refresh companies button
        document.getElementById('refresh-companies')?.addEventListener('click', () => {
            this.loadCompanies();
        });
        
        // Company search
        document.getElementById('company-search')?.addEventListener('input', (e) => {
            this.filterCompanies(e.target.value);
        });
        
        // Load more companies
        document.getElementById('load-more-companies')?.addEventListener('click', () => {
            this.loadMoreCompanies();
        });
        
        // Modal events
        document.getElementById('close-modal')?.addEventListener('click', () => {
            this.closeModal();
        });
        
        document.getElementById('company-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'company-modal') {
                this.closeModal();
            }
        });
        
        // Retry button
        document.getElementById('retry-load')?.addEventListener('click', () => {
            this.loadDashboardData();
        });
        
        // View all history
        document.getElementById('view-all-history')?.addEventListener('click', (e) => {
            e.preventDefault();
            // Navigate to test history page
            window.location.href = '/test-history';
        });
    }
    
    async loadDashboardData() {
        try {
            this.showLoading();
            
            // Load dashboard data
            const dashboardResponse = await API.get('/api/dashboard');
            this.dashboardData = dashboardResponse;
            
            // Load companies
            await this.loadCompanies();
            
            this.renderDashboard();
            this.showContent();
            
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showError();
            UI.showError('Failed to load dashboard data. Please try again.');
        }
    }
    
    async loadCompanies() {
        try {
            const companiesResponse = await API.get('/api/companies?include_stats=true');
            this.companies = companiesResponse.companies || [];
            this.filteredCompanies = [...this.companies];
            this.renderCompanies();
        } catch (error) {
            console.error('Error loading companies:', error);
            UI.showError('Failed to load companies data.');
        }
    }
    
    renderDashboard() {
        if (!this.dashboardData) return;
        
        const { user_info, statistics, recent_attempts, progress_by_subject, recommended_companies } = this.dashboardData;
        
        // Update user name
        document.getElementById('user-name').textContent = user_info.name;
        
        // Update statistics
        document.getElementById('total-tests').textContent = statistics.total_tests_taken;
        document.getElementById('average-score').textContent = `${statistics.average_score}%`;
        document.getElementById('best-score').textContent = `${statistics.best_score}%`;
        document.getElementById('tests-this-week').textContent = statistics.tests_this_week;
        
        // Render recent activity
        this.renderRecentActivity(recent_attempts);
        
        // Render progress overview
        this.renderProgressOverview(progress_by_subject);
        
        // Render recommendations
        this.renderRecommendations(recommended_companies);
    }
    
    renderRecentActivity(recentAttempts) {
        const container = document.getElementById('recent-activity');
        if (!container) return;
        
        if (!recentAttempts || recentAttempts.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4 text-gray-500">
                    <p>No recent activity</p>
                    <p class="text-sm">Start taking tests to see your progress here!</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = recentAttempts.map(attempt => `
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                    <p class="font-medium text-sm text-gray-900">${attempt.company}</p>
                    <p class="text-xs text-gray-600">${this.formatDate(attempt.completed_at)}</p>
                </div>
                <div class="text-right">
                    <p class="font-semibold text-sm ${this.getScoreColor(attempt.percentage)}">${attempt.percentage}%</p>
                    <p class="text-xs text-gray-600">${attempt.score}/${attempt.total_questions}</p>
                </div>
            </div>
        `).join('');
    }
    
    renderProgressOverview(progressData) {
        const container = document.getElementById('progress-overview');
        if (!container) return;
        
        if (!progressData || progressData.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4 text-gray-500">
                    <p class="text-sm">No progress data available</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = progressData.map(progress => `
            <div class="space-y-2">
                <div class="flex justify-between items-center">
                    <span class="text-sm font-medium text-gray-700">${progress.subject}</span>
                    <span class="text-sm text-gray-600">${progress.accuracy_rate}%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                         style="width: ${progress.accuracy_rate}%"></div>
                </div>
                <div class="flex justify-between text-xs text-gray-500">
                    <span>${progress.total_attempts} attempts</span>
                    <span class="capitalize">${progress.trend}</span>
                </div>
            </div>
        `).join('');
    }
    
    renderRecommendations(recommendations) {
        const container = document.getElementById('recommendations');
        if (!container) return;
        
        if (!recommendations || recommendations.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4 text-gray-500">
                    <p class="text-sm">Take more tests to get personalized recommendations!</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = recommendations.map(rec => `
            <div class="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div class="flex items-center justify-between mb-2">
                    <h4 class="font-medium text-sm text-blue-900">${rec.company}</h4>
                    <span class="text-xs px-2 py-1 bg-blue-200 text-blue-800 rounded-full">${rec.confidence}</span>
                </div>
                <p class="text-xs text-blue-700">${rec.reason}</p>
                <button class="mt-2 text-xs text-blue-600 hover:text-blue-800 font-medium" 
                        onclick="dashboard.selectCompany('${rec.company}')">
                    Start Test →
                </button>
            </div>
        `).join('');
    }
    
    renderCompanies() {
        const container = document.getElementById('companies-grid');
        if (!container) return;
        
        const startIndex = 0;
        const endIndex = this.currentPage * this.companiesPerPage;
        const companiesToShow = this.filteredCompanies.slice(startIndex, endIndex);
        
        if (companiesToShow.length === 0) {
            container.innerHTML = `
                <div class="col-span-2 text-center py-8 text-gray-500">
                    <p>No companies found matching your search.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = companiesToShow.map(company => `
            <div class="company-card bg-white border border-gray-200 rounded-lg p-4 hover:shadow-lg transition-all duration-200" 
                 onclick="dashboard.selectCompany('${company.name}')">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="font-semibold text-gray-900">${company.name}</h3>
                    ${company.supported ? 
                        '<span class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Supported</span>' : 
                        '<span class="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">Custom</span>'
                    }
                </div>
                
                <div class="space-y-2 text-sm text-gray-600">
                    <div class="flex justify-between">
                        <span>Available Tests:</span>
                        <span class="font-medium">${company.test_count}</span>
                    </div>
                    ${company.user_stats ? `
                        <div class="flex justify-between">
                            <span>Your Attempts:</span>
                            <span class="font-medium">${company.user_stats.attempts}</span>
                        </div>
                        ${company.user_stats.best_score > 0 ? `
                            <div class="flex justify-between">
                                <span>Best Score:</span>
                                <span class="font-medium ${this.getScoreColor(company.user_stats.best_score)}">${company.user_stats.best_score}%</span>
                            </div>
                        ` : ''}
                    ` : ''}
                </div>
                
                <div class="mt-4 pt-3 border-t border-gray-100">
                    <button class="w-full text-blue-600 hover:text-blue-800 font-medium text-sm">
                        ${company.user_stats && company.user_stats.attempts > 0 ? 'Take Another Test' : 'Start First Test'}
                    </button>
                </div>
            </div>
        `).join('');
        
        // Show/hide load more button
        const loadMoreBtn = document.getElementById('load-more-companies');
        if (loadMoreBtn) {
            if (endIndex < this.filteredCompanies.length) {
                loadMoreBtn.classList.remove('hidden');
            } else {
                loadMoreBtn.classList.add('hidden');
            }
        }
    }
    
    filterCompanies(searchTerm) {
        const term = searchTerm.toLowerCase().trim();
        
        if (term === '') {
            this.filteredCompanies = [...this.companies];
        } else {
            this.filteredCompanies = this.companies.filter(company => 
                company.name.toLowerCase().includes(term)
            );
        }
        
        this.currentPage = 1;
        this.renderCompanies();
    }
    
    loadMoreCompanies() {
        this.currentPage++;
        this.renderCompanies();
    }
    
    async selectCompany(companyName) {
        try {
            const company = this.companies.find(c => c.name === companyName);
            if (!company) return;
            
            // Show modal with company details
            this.showCompanyModal(company);
            
        } catch (error) {
            console.error('Error selecting company:', error);
            UI.showError('Failed to load company details.');
        }
    }
    
    showCompanyModal(company) {
        const modal = document.getElementById('company-modal');
        const companyName = document.getElementById('modal-company-name');
        const companyStats = document.getElementById('modal-company-stats');
        
        if (!modal || !companyName || !companyStats) return;
        
        companyName.textContent = company.name;
        
        // Render company statistics
        companyStats.innerHTML = `
            <div class="grid grid-cols-2 gap-4 text-sm">
                <div class="text-center p-3 bg-gray-50 rounded-lg">
                    <div class="font-semibold text-lg text-blue-600">${company.test_count}</div>
                    <div class="text-gray-600">Available Tests</div>
                </div>
                <div class="text-center p-3 bg-gray-50 rounded-lg">
                    <div class="font-semibold text-lg text-green-600">${company.user_stats ? company.user_stats.attempts : 0}</div>
                    <div class="text-gray-600">Your Attempts</div>
                </div>
                ${company.user_stats && company.user_stats.best_score > 0 ? `
                    <div class="col-span-2 text-center p-3 bg-gray-50 rounded-lg">
                        <div class="font-semibold text-lg ${this.getScoreColor(company.user_stats.best_score)}">${company.user_stats.best_score}%</div>
                        <div class="text-gray-600">Your Best Score</div>
                    </div>
                ` : ''}
            </div>
            ${company.user_stats && company.user_stats.last_attempt ? `
                <div class="mt-4 text-sm text-gray-600">
                    Last attempt: ${this.formatDate(company.user_stats.last_attempt)}
                </div>
            ` : ''}
        `;
        
        // Set up modal buttons
        const startTestBtn = document.getElementById('start-test');
        const practiceModeBtn = document.getElementById('practice-mode');
        
        if (startTestBtn) {
            startTestBtn.onclick = () => this.startTest(company.name, false);
        }
        
        if (practiceModeBtn) {
            practiceModeBtn.onclick = () => this.startTest(company.name, true);
        }
        
        modal.classList.remove('hidden');
    }
    
    closeModal() {
        const modal = document.getElementById('company-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
    
    async startTest(companyName, practiceMode = false) {
        try {
            this.closeModal();
            UI.showSuccess(`Generating ${practiceMode ? 'practice' : ''} test for ${companyName}...`);
            
            // Generate test
            const response = await API.post(`/api/tests/generate/${encodeURIComponent(companyName)}`, {
                practice_mode: practiceMode
            });
            
            if (response.test_id) {
                // Navigate to test page
                window.location.href = `/test/${response.test_id}`;
            } else {
                throw new Error('No test ID received');
            }
            
        } catch (error) {
            console.error('Error starting test:', error);
            UI.showError(`Failed to generate test for ${companyName}. Please try again.`);
        }
    }
    
    // Utility methods
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) {
            return 'Yesterday';
        } else if (diffDays < 7) {
            return `${diffDays} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    }
    
    getScoreColor(score) {
        if (score >= 80) return 'text-green-600';
        if (score >= 60) return 'text-yellow-600';
        return 'text-red-600';
    }
    
    showLoading() {
        document.getElementById('loading-state')?.classList.remove('hidden');
        document.getElementById('dashboard-content')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
    }
    
    showContent() {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('dashboard-content')?.classList.remove('hidden');
        document.getElementById('error-state')?.classList.add('hidden');
    }
    
    showError() {
        document.getElementById('loading-state')?.classList.add('hidden');
        document.getElementById('dashboard-content')?.classList.add('hidden');
        document.getElementById('error-state')?.classList.remove('hidden');
    }
}

// Initialize dashboard when DOM is loaded
let dashboard;
document.addEventListener('DOMContentLoaded', function() {
    dashboard = new Dashboard();
});

// Export for global access
window.dashboard = dashboard;