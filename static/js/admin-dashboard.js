/**
 * Admin Dashboard JavaScript
 * Handles admin panel functionality including student management, test creation, and analytics
 */

// Global variables
let currentStudentsPage = 1;
let currentTestsPage = 1;
let studentsPerPage = 20;
let testsPerPage = 20;
let questionCount = 0;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

/**
 * Initialize the admin dashboard
 */
function initializeDashboard() {
    // Load initial data
    loadStudents();
    loadTests();
    loadAnalytics();
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize charts
    initializeCharts();
    
    console.log('Admin dashboard initialized');
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Student search
    const studentSearch = document.getElementById('student-search');
    if (studentSearch) {
        studentSearch.addEventListener('input', debounce(filterStudents, 300));
    }
    
    // Form submissions
    const createTestForm = document.getElementById('create-test-form');
    if (createTestForm) {
        createTestForm.addEventListener('submit', handleCreateTest);
    }
    
    // Navigation tabs
    setupTabNavigation();
}

/**
 * Set up tab navigation
 */
function setupTabNavigation() {
    const navLinks = document.querySelectorAll('nav a[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            showSection(targetId);
            updateActiveTab(this);
        });
    });
}

/**
 * Show specific section and hide others
 */
function showSection(sectionId) {
    const sections = ['overview', 'students', 'tests', 'analytics'];
    sections.forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            section.style.display = id === sectionId ? 'block' : 'none';
        }
    });
}

/**
 * Update active tab styling
 */
function updateActiveTab(activeLink) {
    const navLinks = document.querySelectorAll('nav a[href^="#"]');
    navLinks.forEach(link => {
        link.classList.remove('border-blue-500', 'text-gray-900');
        link.classList.add('border-transparent', 'text-gray-500');
    });
    
    activeLink.classList.remove('border-transparent', 'text-gray-500');
    activeLink.classList.add('border-blue-500', 'text-gray-900');
}

/**
 * Load students data
 */
async function loadStudents(page = 1) {
    try {
        showLoading();
        
        const params = new URLSearchParams({
            page: page,
            per_page: studentsPerPage
        });
        
        // Add filters if set
        const search = document.getElementById('student-search')?.value;
        const branch = document.getElementById('branch-filter')?.value;
        const year = document.getElementById('year-filter')?.value;
        
        if (search) params.append('search', search);
        if (branch) params.append('branch', branch);
        if (year) params.append('year', year);
        
        const response = await fetch(`/admin/api/students?${params}`);
        const data = await response.json();
        
        if (data.success) {
            displayStudents(data.students);
            displayStudentsPagination(data.pagination);
            currentStudentsPage = page;
        } else {
            showError('Failed to load students: ' + data.error);
        }
    } catch (error) {
        console.error('Error loading students:', error);
        showError('Failed to load students');
    } finally {
        hideLoading();
    }
}

/**
 * Display students in table
 */
function displayStudents(students) {
    const tbody = document.getElementById('students-table-body');
    if (!tbody) return;
    
    if (students.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-4 text-center text-gray-500">
                    No students found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = students.map(student => `
        <tr class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                        <div class="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                            <span class="text-sm font-medium text-gray-700">
                                ${student.name.charAt(0).toUpperCase()}
                            </span>
                        </div>
                    </div>
                    <div class="ml-4">
                        <div class="text-sm font-medium text-gray-900">${escapeHtml(student.name)}</div>
                        <div class="text-sm text-gray-500">${escapeHtml(student.email)}</div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">${escapeHtml(student.branch || 'N/A')}</div>
                <div class="text-sm text-gray-500">Year ${student.year || 'N/A'}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${student.total_attempts || 0}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${student.average_score ? student.average_score.toFixed(1) + '%' : 'N/A'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${student.last_activity ? formatDate(student.last_activity) : 'Never'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button onclick="viewStudentDetails(${student.id})" 
                        class="text-blue-600 hover:text-blue-900">
                    View Details
                </button>
            </td>
        </tr>
    `).join('');
}

/**
 * Display students pagination
 */
function displayStudentsPagination(pagination) {
    const container = document.getElementById('students-pagination');
    if (!container) return;
    
    const { page, pages, has_prev, has_next, total } = pagination;
    
    container.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="text-sm text-gray-700">
                Showing page ${page} of ${pages} (${total} total students)
            </div>
            <div class="flex space-x-2">
                <button onclick="loadStudents(${page - 1})" 
                        ${!has_prev ? 'disabled' : ''}
                        class="px-3 py-1 border rounded text-sm ${!has_prev ? 'bg-gray-100 text-gray-400' : 'bg-white text-gray-700 hover:bg-gray-50'}">
                    Previous
                </button>
                <button onclick="loadStudents(${page + 1})" 
                        ${!has_next ? 'disabled' : ''}
                        class="px-3 py-1 border rounded text-sm ${!has_next ? 'bg-gray-100 text-gray-400' : 'bg-white text-gray-700 hover:bg-gray-50'}">
                    Next
                </button>
            </div>
        </div>
    `;
}

/**
 * Load tests data
 */
async function loadTests(page = 1) {
    try {
        showLoading();
        
        const params = new URLSearchParams({
            page: page,
            per_page: testsPerPage
        });
        
        const response = await fetch(`/admin/api/tests?${params}`);
        const data = await response.json();
        
        if (data.success) {
            displayTests(data.tests);
            displayTestsPagination(data.pagination);
            currentTestsPage = page;
        } else {
            showError('Failed to load tests: ' + data.error);
        }
    } catch (error) {
        console.error('Error loading tests:', error);
        showError('Failed to load tests');
    } finally {
        hideLoading();
    }
}

/**
 * Display tests in table
 */
function displayTests(tests) {
    const tbody = document.getElementById('tests-table-body');
    if (!tbody) return;
    
    if (tests.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-6 py-4 text-center text-gray-500">
                    No tests found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = tests.map(test => `
        <tr class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">${escapeHtml(test.company)}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${test.year}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${test.question_count || 0}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${test.attempt_count || 0}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${test.average_score ? test.average_score.toFixed(1) + '%' : 'N/A'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${formatDate(test.created_at)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button onclick="viewTestDetails(${test.id})" 
                        class="text-blue-600 hover:text-blue-900 mr-3">
                    View
                </button>
                <button onclick="editTest(${test.id})" 
                        class="text-green-600 hover:text-green-900">
                    Edit
                </button>
            </td>
        </tr>
    `).join('');
}

/**
 * Display tests pagination
 */
function displayTestsPagination(pagination) {
    const container = document.getElementById('tests-pagination');
    if (!container) return;
    
    const { page, pages, has_prev, has_next, total } = pagination;
    
    container.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="text-sm text-gray-700">
                Showing page ${page} of ${pages} (${total} total tests)
            </div>
            <div class="flex space-x-2">
                <button onclick="loadTests(${page - 1})" 
                        ${!has_prev ? 'disabled' : ''}
                        class="px-3 py-1 border rounded text-sm ${!has_prev ? 'bg-gray-100 text-gray-400' : 'bg-white text-gray-700 hover:bg-gray-50'}">
                    Previous
                </button>
                <button onclick="loadTests(${page + 1})" 
                        ${!has_next ? 'disabled' : ''}
                        class="px-3 py-1 border rounded text-sm ${!has_next ? 'bg-gray-100 text-gray-400' : 'bg-white text-gray-700 hover:bg-gray-50'}">
                    Next
                </button>
            </div>
        </div>
    `;
}

/**
 * Filter students based on search and filters
 */
function filterStudents() {
    loadStudents(1); // Reset to first page when filtering
}

/**
 * Refresh students data
 */
function refreshStudents() {
    loadStudents(currentStudentsPage);
}

/**
 * View student details
 */
async function viewStudentDetails(studentId) {
    try {
        showLoading();
        
        const response = await fetch(`/admin/api/students/${studentId}`);
        const data = await response.json();
        
        if (data.success) {
            displayStudentDetailModal(data.student);
        } else {
            showError('Failed to load student details: ' + data.error);
        }
    } catch (error) {
        console.error('Error loading student details:', error);
        showError('Failed to load student details');
    } finally {
        hideLoading();
    }
}

/**
 * Display student detail modal
 */
function displayStudentDetailModal(student) {
    const modal = document.getElementById('student-detail-modal');
    const title = document.getElementById('student-detail-title');
    const content = document.getElementById('student-detail-content');
    
    if (!modal || !title || !content) return;
    
    title.textContent = `${student.name} - Student Details`;
    
    content.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-4">
                <h4 class="text-lg font-medium text-gray-900">Basic Information</h4>
                <div class="bg-gray-50 p-4 rounded-lg space-y-2">
                    <div><strong>Name:</strong> ${escapeHtml(student.name)}</div>
                    <div><strong>Email:</strong> ${escapeHtml(student.email)}</div>
                    <div><strong>Branch:</strong> ${escapeHtml(student.branch || 'N/A')}</div>
                    <div><strong>Year:</strong> ${student.year || 'N/A'}</div>
                    <div><strong>Joined:</strong> ${formatDate(student.created_at)}</div>
                </div>
                
                <h4 class="text-lg font-medium text-gray-900">Performance Summary</h4>
                <div class="bg-gray-50 p-4 rounded-lg space-y-2">
                    <div><strong>Total Attempts:</strong> ${student.total_attempts || 0}</div>
                    <div><strong>Average Score:</strong> ${student.average_score ? student.average_score.toFixed(1) + '%' : 'N/A'}</div>
                    <div><strong>Weak Areas:</strong> ${student.weak_areas ? student.weak_areas.join(', ') : 'None identified'}</div>
                </div>
            </div>
            
            <div class="space-y-4">
                <h4 class="text-lg font-medium text-gray-900">Recent Test Attempts</h4>
                <div class="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">
                    ${student.test_attempts && student.test_attempts.length > 0 ? 
                        student.test_attempts.slice(0, 10).map(attempt => `
                            <div class="border-b border-gray-200 pb-2 mb-2 last:border-b-0">
                                <div class="flex justify-between items-start">
                                    <div>
                                        <div class="font-medium">${escapeHtml(attempt.test_company || 'Unknown Test')}</div>
                                        <div class="text-sm text-gray-600">${formatDate(attempt.started_at)}</div>
                                    </div>
                                    <div class="text-right">
                                        <div class="font-medium ${attempt.score >= 70 ? 'text-green-600' : attempt.score >= 50 ? 'text-yellow-600' : 'text-red-600'}">
                                            ${attempt.score.toFixed(1)}%
                                        </div>
                                        <div class="text-sm text-gray-600">${attempt.total_questions} questions</div>
                                    </div>
                                </div>
                            </div>
                        `).join('') : 
                        '<p class="text-gray-500">No test attempts yet</p>'
                    }
                </div>
            </div>
        </div>
    `;
    
    modal.classList.remove('hidden');
}

/**
 * Hide student detail modal
 */
function hideStudentDetailModal() {
    const modal = document.getElementById('student-detail-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * Show create test modal
 */
function showCreateTestModal() {
    const modal = document.getElementById('create-test-modal');
    if (modal) {
        // Reset form
        document.getElementById('create-test-form').reset();
        document.getElementById('questions-container').innerHTML = '';
        questionCount = 0;
        
        // Add initial question
        addQuestion();
        
        modal.classList.remove('hidden');
    }
}

/**
 * Hide create test modal
 */
function hideCreateTestModal() {
    const modal = document.getElementById('create-test-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * Add question to test creation form
 */
function addQuestion() {
    questionCount++;
    const container = document.getElementById('questions-container');
    if (!container) return;
    
    const questionDiv = document.createElement('div');
    questionDiv.className = 'border border-gray-200 rounded-lg p-4 mb-4';
    questionDiv.innerHTML = `
        <div class="flex justify-between items-center mb-3">
            <h4 class="text-md font-medium text-gray-900">Question ${questionCount}</h4>
            <button type="button" onclick="removeQuestion(this)" class="text-red-600 hover:text-red-800 text-sm">
                Remove
            </button>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="md:col-span-2">
                <label class="block text-sm font-medium text-gray-700">Question Text</label>
                <textarea name="question_text" required rows="2" 
                          class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                          placeholder="Enter the question..."></textarea>
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700">Section</label>
                <select name="section" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm">
                    <option value="Quantitative Aptitude">Quantitative Aptitude</option>
                    <option value="Logical Reasoning">Logical Reasoning</option>
                    <option value="Verbal Ability">Verbal Ability</option>
                    <option value="Technical">Technical</option>
                    <option value="General Knowledge">General Knowledge</option>
                </select>
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700">Difficulty</label>
                <select name="difficulty" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm">
                    <option value="easy">Easy</option>
                    <option value="medium" selected>Medium</option>
                    <option value="hard">Hard</option>
                </select>
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700">Option A</label>
                <input type="text" name="option_a" required 
                       class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                       placeholder="Option A">
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700">Option B</label>
                <input type="text" name="option_b" required 
                       class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                       placeholder="Option B">
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700">Option C</label>
                <input type="text" name="option_c" required 
                       class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                       placeholder="Option C">
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700">Option D</label>
                <input type="text" name="option_d" required 
                       class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                       placeholder="Option D">
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700">Correct Answer</label>
                <select name="correct_answer" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm">
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                    <option value="D">D</option>
                </select>
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700">Topic (Optional)</label>
                <input type="text" name="topic" 
                       class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                       placeholder="e.g., Algebra, Data Structures">
            </div>
            
            <div class="md:col-span-2">
                <label class="block text-sm font-medium text-gray-700">Explanation (Optional)</label>
                <textarea name="explanation" rows="2" 
                          class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                          placeholder="Explain the correct answer..."></textarea>
            </div>
        </div>
    `;
    
    container.appendChild(questionDiv);
}

/**
 * Remove question from test creation form
 */
function removeQuestion(button) {
    const questionDiv = button.closest('.border');
    if (questionDiv) {
        questionDiv.remove();
        
        // Renumber remaining questions
        const questions = document.querySelectorAll('#questions-container .border h4');
        questions.forEach((h4, index) => {
            h4.textContent = `Question ${index + 1}`;
        });
        
        questionCount = questions.length;
    }
}

/**
 * Handle create test form submission
 */
async function handleCreateTest(event) {
    event.preventDefault();
    
    try {
        showLoading();
        
        const formData = new FormData(event.target);
        const company = formData.get('test-company');
        const year = parseInt(formData.get('test-year'));
        const patternData = formData.get('test-pattern');
        
        // Collect questions
        const questions = [];
        const questionDivs = document.querySelectorAll('#questions-container .border');
        
        questionDivs.forEach(div => {
            const inputs = div.querySelectorAll('input, select, textarea');
            const question = {};
            
            inputs.forEach(input => {
                if (input.name) {
                    question[input.name] = input.value;
                }
            });
            
            // Format options as array
            question.options = [
                question.option_a,
                question.option_b,
                question.option_c,
                question.option_d
            ];
            
            // Remove individual option fields
            delete question.option_a;
            delete question.option_b;
            delete question.option_c;
            delete question.option_d;
            
            questions.push(question);
        });
        
        if (questions.length === 0) {
            showError('Please add at least one question');
            return;
        }
        
        const testData = {
            company: company,
            year: year,
            pattern_data: patternData,
            questions: questions
        };
        
        const response = await fetch('/admin/api/tests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(testData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Test created successfully!');
            hideCreateTestModal();
            loadTests(); // Refresh tests list
        } else {
            showError('Failed to create test: ' + data.error);
        }
    } catch (error) {
        console.error('Error creating test:', error);
        showError('Failed to create test');
    } finally {
        hideLoading();
    }
}

/**
 * Load analytics data
 */
async function loadAnalytics() {
    try {
        const response = await fetch('/admin/api/analytics/overview');
        const data = await response.json();
        
        if (data.success) {
            updateAnalyticsCharts(data.analytics);
        } else {
            console.error('Failed to load analytics:', data.error);
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

/**
 * Initialize charts
 */
function initializeCharts() {
    // Performance chart
    const performanceCtx = document.getElementById('performance-chart');
    if (performanceCtx) {
        window.performanceChart = new Chart(performanceCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Average Score',
                    data: [],
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
    
    // Activity chart
    const activityCtx = document.getElementById('activity-chart');
    if (activityCtx) {
        window.activityChart = new Chart(activityCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Test Attempts',
                    data: [],
                    backgroundColor: 'rgba(34, 197, 94, 0.8)',
                    borderColor: 'rgb(34, 197, 94)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}

/**
 * Update analytics charts with data
 */
function updateAnalyticsCharts(analytics) {
    // Update performance chart with dummy data for now
    if (window.performanceChart) {
        window.performanceChart.data.labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
        window.performanceChart.data.datasets[0].data = [65, 70, 75, analytics.performance?.average_score || 0];
        window.performanceChart.update();
    }
    
    // Update activity chart with dummy data for now
    if (window.activityChart) {
        window.activityChart.data.labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        window.activityChart.data.datasets[0].data = [12, 19, 15, 25, 22, 18, 20];
        window.activityChart.update();
    }
}

/**
 * Utility functions
 */

function showLoading() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.classList.remove('hidden');
    }
}

function hideLoading() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.classList.add('hidden');
    }
}

function showError(message) {
    // Create and show error notification
    const notification = document.createElement('div');
    notification.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50';
    notification.innerHTML = `
        <div class="flex items-center">
            <span>${escapeHtml(message)}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-red-500 hover:text-red-700">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                </svg>
            </button>
        </div>
    `;
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function showSuccess(message) {
    // Create and show success notification
    const notification = document.createElement('div');
    notification.className = 'fixed top-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded z-50';
    notification.innerHTML = `
        <div class="flex items-center">
            <span>${escapeHtml(message)}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-green-500 hover:text-green-700">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                </svg>
            </button>
        </div>
    `;
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 3000);
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Placeholder functions for future implementation
function viewTestDetails(testId) {
    console.log('View test details:', testId);
    showError('Test details view not implemented yet');
}

function editTest(testId) {
    console.log('Edit test:', testId);
    showError('Test editing not implemented yet');
}