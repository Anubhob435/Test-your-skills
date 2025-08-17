// Utility functions for UEM Placement Preparation Platform

// API utility functions
const API = {
    // Base API call function
    async call(endpoint, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(endpoint, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'API call failed');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // GET request
    async get(endpoint) {
        return this.call(endpoint, { method: 'GET' });
    },

    // POST request
    async post(endpoint, data) {
        return this.call(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    // PUT request
    async put(endpoint, data) {
        return this.call(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },

    // DELETE request
    async delete(endpoint) {
        return this.call(endpoint, { method: 'DELETE' });
    }
};

// UI utility functions
const UI = {
    // Show loading spinner
    showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '<div class="spinner"></div>';
        }
    },

    // Hide loading spinner
    hideLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '';
        }
    },

    // Show alert message
    showAlert(message, type = 'info', duration = 5000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} fixed top-4 right-4 z-50 max-w-sm`;
        alertDiv.innerHTML = `
            <div class="flex justify-between items-center">
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-lg">&times;</button>
            </div>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (alertDiv.parentElement) {
                    alertDiv.remove();
                }
            }, duration);
        }
    },

    // Show success message
    showSuccess(message, duration = 5000) {
        this.showAlert(message, 'success', duration);
    },

    // Show error message
    showError(message, duration = 5000) {
        this.showAlert(message, 'error', duration);
    },

    // Show warning message
    showWarning(message, duration = 5000) {
        this.showAlert(message, 'warning', duration);
    },

    // Confirm dialog
    confirm(message, callback) {
        if (window.confirm(message)) {
            callback();
        }
    }
};

// Form utility functions
const Form = {
    // Serialize form data to JSON
    serialize(formElement) {
        const formData = new FormData(formElement);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        return data;
    },

    // Validate email format
    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    // Validate UEM email
    validateUEMEmail(email) {
        return email.endsWith('@uem.edu.in');
    },

    // Validate password strength
    validatePassword(password) {
        return password.length >= 8;
    },

    // Clear form errors
    clearErrors(formElement) {
        const errorElements = formElement.querySelectorAll('.error-message');
        errorElements.forEach(element => element.remove());
        
        const inputElements = formElement.querySelectorAll('.border-red-500');
        inputElements.forEach(element => {
            element.classList.remove('border-red-500');
            element.classList.add('border-gray-300');
        });
    },

    // Show field error
    showFieldError(fieldElement, message) {
        // Remove existing error
        const existingError = fieldElement.parentElement.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }

        // Add error styling
        fieldElement.classList.remove('border-gray-300');
        fieldElement.classList.add('border-red-500');

        // Add error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message text-red-600 text-sm mt-1';
        errorDiv.textContent = message;
        fieldElement.parentElement.appendChild(errorDiv);
    }
};

// Timer utility functions
const Timer = {
    // Format seconds to MM:SS format
    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    },

    // Create countdown timer
    createCountdown(duration, elementId, onComplete) {
        let timeLeft = duration;
        const element = document.getElementById(elementId);
        
        const updateTimer = () => {
            if (element) {
                element.textContent = this.formatTime(timeLeft);
                
                // Add warning classes
                if (timeLeft <= 300) { // 5 minutes
                    element.parentElement.classList.add('warning');
                }
                if (timeLeft <= 60) { // 1 minute
                    element.parentElement.classList.add('danger');
                }
            }
            
            if (timeLeft <= 0) {
                clearInterval(interval);
                if (onComplete) {
                    onComplete();
                }
            } else {
                timeLeft--;
            }
        };
        
        updateTimer(); // Initial call
        const interval = setInterval(updateTimer, 1000);
        
        return interval;
    }
};

// Local storage utility functions
const Storage = {
    // Set item in localStorage
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('Error saving to localStorage:', error);
        }
    },

    // Get item from localStorage
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Error reading from localStorage:', error);
            return defaultValue;
        }
    },

    // Remove item from localStorage
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('Error removing from localStorage:', error);
        }
    },

    // Clear all localStorage
    clear() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('Error clearing localStorage:', error);
        }
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add any global initialization code here
    console.log('UEM Placement Preparation Platform loaded');
    
    // Add click handlers for mobile menu toggle
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }
});

// Export utilities for use in other scripts
window.API = API;
window.UI = UI;
window.Form = Form;
window.Timer = Timer;
window.Storage = Storage;