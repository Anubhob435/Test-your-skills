/**
 * Leaderboard JavaScript functionality
 * Handles leaderboard display, filtering, pagination, and user position
 */

class LeaderboardManager {
    constructor() {
        this.currentPage = 1;
        this.currentFilters = {
            company: '',
            year: '',
            branch: ''
        };
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadFilters();
        this.loadStats();
        this.loadUserPosition();
        this.loadLeaderboard();
    }
    
    bindEvents() {
        // Filter change events
        document.getElementById('companyFilter').addEventListener('change', () => this.onFilterChange());
        document.getElementById('yearFilter').addEventListener('change', () => this.onFilterChange());
        document.getElementById('branchFilter').addEventListener('change', () => this.onFilterChange());
        
        // Clear filters button
        document.getElementById('clearFilters').addEventListener('click', () => this.clearFilters());
        
        // Pagination events (will be bound dynamically)
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('pagination-btn')) {
                const page = parseInt(e.target.dataset.page);
                if (page && page !== this.currentPage) {
                    this.currentPage = page;
                    this.loadLeaderboard();
                }
            }
        });
    }
    
    async loadFilters() {
        try {
            const response = await fetch('/api/leaderboard/filters');
            const data = await response.json();
            
            if (data.success) {
                this.populateFilterOptions(data.data);
            }
        } catch (error) {
            console.error('Error loading filters:', error);
        }
    }
    
    populateFilterOptions(filters) {
        // Populate company filter
        const companySelect = document.getElementById('companyFilter');
        filters.companies.forEach(company => {
            const option = document.createElement('option');
            option.value = company;
            option.textContent = company;
            companySelect.appendChild(option);
        });
        
        // Populate year filter
        const yearSelect = document.getElementById('yearFilter');
        filters.years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearSelect.appendChild(option);
        });
        
        // Populate branch filter
        const branchSelect = document.getElementById('branchFilter');
        filters.branches.forEach(branch => {
            const option = document.createElement('option');
            option.value = branch;
            option.textContent = branch;
            branchSelect.appendChild(option);
        });
    }
    
    async loadStats() {
        try {
            const response = await fetch('/api/leaderboard/stats');
            const data = await response.json();
            
            if (data.success) {
                this.updateStatsCards(data.data);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    updateStatsCards(stats) {
        document.getElementById('totalParticipants').textContent = stats.total_participants.toLocaleString();
        document.getElementById('totalTests').textContent = stats.total_tests_taken.toLocaleString();
        document.getElementById('platformAverage').textContent = `${stats.platform_average}%`;
        document.getElementById('highestScore').textContent = `${stats.highest_score}%`;
    }
    
    async loadUserPosition() {
        try {
            const queryParams = new URLSearchParams(this.currentFilters);
            const response = await fetch(`/api/leaderboard/position?${queryParams}`);
            const data = await response.json();
            
            if (data.success && data.data.user_position) {
                this.updateUserPositionCard(data.data);
            } else {
                // Hide user position card if user is not qualified
                document.getElementById('userPositionCard').style.display = 'none';
            }
        } catch (error) {
            console.error('Error loading user position:', error);
        }
    }
    
    updateUserPositionCard(positionData) {
        const card = document.getElementById('userPositionCard');
        const userEntry = positionData.user_entry;
        
        document.getElementById('userRank').textContent = `#${positionData.user_position}`;
        document.getElementById('userScore').textContent = `${userEntry.average_score}%`;
        document.getElementById('userTests').textContent = userEntry.total_tests;
        
        card.style.display = 'block';
    }
    
    async loadLeaderboard() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const queryParams = new URLSearchParams({
                page: this.currentPage,
                limit: 20,
                ...this.currentFilters
            });
            
            const response = await fetch(`/api/leaderboard/?${queryParams}`);
            const data = await response.json();
            
            if (data.success) {
                this.updateLeaderboardTable(data.data);
                this.updatePagination(data.data.pagination);
            } else {
                this.showError('Failed to load leaderboard data');
            }
        } catch (error) {
            console.error('Error loading leaderboard:', error);
            this.showError('Network error occurred');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    updateLeaderboardTable(leaderboardData) {
        const tbody = document.getElementById('leaderboardTableBody');
        const leaderboard = leaderboardData.leaderboard;
        
        if (leaderboard.length === 0) {
            this.showEmptyState();
            return;
        }
        
        this.hideEmptyState();
        
        tbody.innerHTML = '';
        
        leaderboard.forEach(entry => {
            const row = this.createLeaderboardRow(entry);
            tbody.appendChild(row);
        });
        
        document.getElementById('leaderboardContent').style.display = 'block';
    }
    
    createLeaderboardRow(entry) {
        const row = document.createElement('tr');
        row.className = 'leaderboard-card hover:bg-gray-50';
        
        // Add special styling for current user
        if (entry.is_current_user) {
            row.className += ' bg-blue-50 border-l-4 border-blue-500';
        }
        
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <span class="rank-badge ${this.getRankClass(entry.rank)} text-white text-sm font-bold px-3 py-1 rounded-full">
                        ${entry.rank}
                    </span>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                        <div class="h-10 w-10 rounded-full bg-gradient-to-r from-blue-400 to-purple-500 flex items-center justify-center text-white font-semibold">
                            ${entry.name.charAt(0).toUpperCase()}
                        </div>
                    </div>
                    <div class="ml-4">
                        <div class="text-sm font-medium text-gray-900">
                            ${entry.name}
                            ${entry.is_current_user ? '<span class="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">You</span>' : ''}
                        </div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${entry.year || 'N/A'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${entry.branch || 'N/A'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${entry.total_tests}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <span class="text-sm font-medium text-gray-900">${entry.average_score}%</span>
                    <div class="ml-2 w-16 bg-gray-200 rounded-full h-2">
                        <div class="bg-gradient-to-r from-green-400 to-blue-500 h-2 rounded-full" style="width: ${entry.average_score}%"></div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${entry.total_time_hours}h
            </td>
        `;
        
        return row;
    }
    
    getRankClass(rank) {
        if (rank === 1) return 'rank-1';
        if (rank === 2) return 'rank-2';
        if (rank === 3) return 'rank-3';
        return '';
    }
    
    updatePagination(pagination) {
        const nav = document.getElementById('paginationNav');
        const showingFrom = ((pagination.current_page - 1) * pagination.per_page) + 1;
        const showingTo = Math.min(pagination.current_page * pagination.per_page, pagination.total_count);
        
        // Update pagination info
        document.getElementById('showingFrom').textContent = showingFrom;
        document.getElementById('showingTo').textContent = showingTo;
        document.getElementById('totalCount').textContent = pagination.total_count;
        
        // Clear existing pagination
        nav.innerHTML = '';
        
        // Previous button
        if (pagination.has_prev) {
            nav.appendChild(this.createPaginationButton(pagination.current_page - 1, 'Previous', 'prev'));
        }
        
        // Page numbers
        const startPage = Math.max(1, pagination.current_page - 2);
        const endPage = Math.min(pagination.total_pages, pagination.current_page + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            nav.appendChild(this.createPaginationButton(i, i.toString(), i === pagination.current_page ? 'current' : 'page'));
        }
        
        // Next button
        if (pagination.has_next) {
            nav.appendChild(this.createPaginationButton(pagination.current_page + 1, 'Next', 'next'));
        }
    }
    
    createPaginationButton(page, text, type) {
        const button = document.createElement('button');
        button.className = 'pagination-btn relative inline-flex items-center px-4 py-2 border text-sm font-medium';
        button.dataset.page = page;
        button.textContent = text;
        
        if (type === 'current') {
            button.className += ' z-10 bg-blue-50 border-blue-500 text-blue-600';
        } else {
            button.className += ' bg-white border-gray-300 text-gray-500 hover:bg-gray-50';
        }
        
        return button;
    }
    
    onFilterChange() {
        // Update current filters
        this.currentFilters.company = document.getElementById('companyFilter').value;
        this.currentFilters.year = document.getElementById('yearFilter').value;
        this.currentFilters.branch = document.getElementById('branchFilter').value;
        
        // Reset to first page
        this.currentPage = 1;
        
        // Reload data
        this.loadLeaderboard();
        this.loadUserPosition();
    }
    
    clearFilters() {
        // Reset filter selects
        document.getElementById('companyFilter').value = '';
        document.getElementById('yearFilter').value = '';
        document.getElementById('branchFilter').value = '';
        
        // Reset filters object
        this.currentFilters = {
            company: '',
            year: '',
            branch: ''
        };
        
        // Reset to first page
        this.currentPage = 1;
        
        // Reload data
        this.loadLeaderboard();
        this.loadUserPosition();
    }
    
    showLoading() {
        document.getElementById('loadingState').style.display = 'flex';
        document.getElementById('leaderboardContent').style.display = 'none';
        document.getElementById('emptyState').style.display = 'none';
    }
    
    hideLoading() {
        document.getElementById('loadingState').style.display = 'none';
    }
    
    showEmptyState() {
        document.getElementById('emptyState').style.display = 'block';
        document.getElementById('leaderboardContent').style.display = 'none';
    }
    
    hideEmptyState() {
        document.getElementById('emptyState').style.display = 'none';
    }
    
    showError(message) {
        // You can implement a toast notification system here
        console.error('Leaderboard Error:', message);
        alert(`Error: ${message}`);
    }
}

// Initialize leaderboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new LeaderboardManager();
});