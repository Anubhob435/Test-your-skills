/**
 * Profile Page JavaScript
 * Handles progress visualization, analytics, and user interactions
 */

class ProfileManager {
    constructor() {
        this.trendChart = null;
        this.init();
    }

    async init() {
        try {
            await this.loadProfileData();
            this.hideLoading();
            this.showContent();
        } catch (error) {
            console.error('Error initializing profile:', error);
            this.showError('Failed to load profile data. Please refresh the page.');
        }
    }

    async loadProfileData() {
        // Load all profile data in parallel
        const [stats, progress, recommendations, weakAreas, testHistory] = await Promise.all([
            this.fetchUserStats(),
            this.fetchUserProgress(),
            this.fetchRecommendations(),
            this.fetchWeakAreas(),
            this.fetchTestHistory(1, 5) // First page, 5 items for recent history
        ]);

        // Update UI with loaded data
        this.updateStatsCards(stats);
        this.updatePerformanceTrend(progress.recent_performance);
        this.updateSubjectPerformance(progress.subject_performance);
        this.updateRecommendations(recommendations);
        this.updateWeakAreas(weakAreas);
        this.updateTestHistory(testHistory.attempts);
    }

    async fetchUserStats() {
        const response = await fetch('/api/profile/stats');
        if (!response.ok) {
            throw new Error('Failed to fetch user statistics');
        }
        const data = await response.json();
        return data.data;
    }

    async fetchUserProgress() {
        const response = await fetch('/api/profile/progress');
        if (!response.ok) {
            throw new Error('Failed to fetch user progress');
        }
        const data = await response.json();
        return data.data;
    }

    async fetchRecommendations() {
        const response = await fetch('/api/profile/recommendations');
        if (!response.ok) {
            throw new Error('Failed to fetch recommendations');
        }
        const data = await response.json();
        return data.data;
    }

    async fetchWeakAreas() {
        const response = await fetch('/api/profile/weak-areas');
        if (!response.ok) {
            throw new Error('Failed to fetch weak areas');
        }
        const data = await response.json();
        return data.data;
    }

    async fetchTestHistory(page = 1, perPage = 10) {
        const response = await fetch(`/api/profile/test-history?page=${page}&per_page=${perPage}`);
        if (!response.ok) {
            throw new Error('Failed to fetch test history');
        }
        const data = await response.json();
        return data.data;
    }

    updateStatsCards(stats) {
        document.getElementById('total-tests').textContent = stats.total_tests || 0;
        document.getElementById('average-score').textContent = `${stats.average_score || 0}%`;
        document.getElementById('best-score').textContent = `${stats.best_score || 0}%`;
        document.getElementById('time-spent').textContent = `${stats.total_time_hours || 0} hrs`;
    }

    updatePerformanceTrend(recentPerformance) {
        const ctx = document.getElementById('trendChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.trendChart) {
            this.trendChart.destroy();
        }

        const labels = recentPerformance.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        const scores = recentPerformance.map(item => item.score);

        this.trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Score %',
                    data: scores,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Score: ${context.parsed.y}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    updateSubjectPerformance(subjectPerformance) {
        const container = document.getElementById('subject-performance');
        container.innerHTML = '';

        if (!subjectPerformance || Object.keys(subjectPerformance).length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-4">No subject data available yet. Take some tests to see your performance!</p>';
            return;
        }

        Object.entries(subjectPerformance).forEach(([subject, data]) => {
            const accuracy = data.accuracy_rate || 0;
            const attempts = data.total_attempts || 0;
            
            const subjectDiv = document.createElement('div');
            subjectDiv.className = 'flex items-center justify-between';
            
            const color = this.getPerformanceColor(accuracy);
            
            subjectDiv.innerHTML = `
                <div class="flex-1">
                    <div class="flex justify-between items-center mb-1">
                        <span class="text-sm font-medium text-gray-700">${subject}</span>
                        <span class="text-sm text-gray-500">${accuracy.toFixed(1)}% (${attempts} tests)</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="h-2 rounded-full ${color}" style="width: ${accuracy}%"></div>
                    </div>
                </div>
            `;
            
            container.appendChild(subjectDiv);
        });
    }

    updateRecommendations(recommendations) {
        const container = document.getElementById('recommendations');
        container.innerHTML = '';

        if (!recommendations.next_steps || recommendations.next_steps.length === 0) {
            container.innerHTML = '<p class="text-gray-500">Take more tests to get personalized recommendations!</p>';
            return;
        }

        recommendations.next_steps.slice(0, 5).forEach(step => {
            const stepDiv = document.createElement('div');
            stepDiv.className = 'flex items-start space-x-3 p-3 bg-blue-50 rounded-lg';
            
            stepDiv.innerHTML = `
                <div class="flex-shrink-0">
                    <svg class="w-5 h-5 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                </div>
                <p class="text-sm text-blue-800">${step}</p>
            `;
            
            container.appendChild(stepDiv);
        });
    }

    updateWeakAreas(weakAreas) {
        const container = document.getElementById('weak-areas');
        container.innerHTML = '';

        if (!weakAreas || weakAreas.length === 0) {
            container.innerHTML = '<p class="text-gray-500">Great job! No significant weak areas identified.</p>';
            return;
        }

        weakAreas.slice(0, 3).forEach(area => {
            const areaDiv = document.createElement('div');
            areaDiv.className = 'p-3 bg-red-50 rounded-lg';
            
            areaDiv.innerHTML = `
                <div class="flex justify-between items-center mb-2">
                    <h4 class="font-medium text-red-800">${area.subject}</h4>
                    <span class="text-sm text-red-600">${area.accuracy_rate.toFixed(1)}%</span>
                </div>
                <p class="text-sm text-red-700">${area.improvement_suggestion}</p>
            `;
            
            container.appendChild(areaDiv);
        });
    }

    updateTestHistory(testHistory) {
        const tbody = document.getElementById('test-history');
        tbody.innerHTML = '';

        if (!testHistory || testHistory.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-4 text-center text-gray-500">
                        No test history available. <a href="/dashboard" class="text-blue-600 hover:text-blue-800">Take your first test!</a>
                    </td>
                </tr>
            `;
            return;
        }

        testHistory.forEach(attempt => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50';
            
            const date = new Date(attempt.started_at);
            const formattedDate = date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
            
            const timeFormatted = this.formatTime(attempt.time_taken);
            const scoreColor = this.getScoreColor(attempt.percentage);
            
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">${attempt.company || 'Unknown'}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${scoreColor}">
                        ${attempt.percentage.toFixed(1)}%
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${timeFormatted}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${formattedDate}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <a href="/test/${attempt.test_id}/results/${attempt.id}" class="text-blue-600 hover:text-blue-900">
                        View Results
                    </a>
                </td>
            `;
            
            tbody.appendChild(row);
        });
    }

    getPerformanceColor(accuracy) {
        if (accuracy >= 80) return 'bg-green-500';
        if (accuracy >= 60) return 'bg-yellow-500';
        return 'bg-red-500';
    }

    getScoreColor(percentage) {
        if (percentage >= 80) return 'bg-green-100 text-green-800';
        if (percentage >= 60) return 'bg-yellow-100 text-yellow-800';
        return 'bg-red-100 text-red-800';
    }

    formatTime(seconds) {
        if (!seconds) return 'N/A';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    }

    showError(message) {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('content').classList.add('hidden');
        document.getElementById('error-message').textContent = message;
        document.getElementById('error').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading').classList.add('hidden');
    }

    showContent() {
        document.getElementById('content').classList.remove('hidden');
    }
}

// Initialize profile manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ProfileManager();
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProfileManager;
}