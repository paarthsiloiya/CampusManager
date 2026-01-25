/**
 * Unified Notification Manager
 * Single source of truth for ALL notifications (real-time, flash, cross-instance)
 */

class UnifiedNotificationManager {
    constructor() {
        this.container = null;
        this.socket = null;
        this.notifications = new Map();
        this.notificationCount = 0;
        this.timers = new Map(); // Track active timers
        
        this.init();
    }
    
    init() {
        console.log('🚀 Initializing Unified Notification System...');
        
        // Create notification container
        this.createContainer();
        
        // Handle server flash messages from window.serverFlashMessages
        this.handleServerFlashMessages();
        
        // Initialize Socket.IO for real-time notifications
        if (window.isAuthenticated) {
            this.initSocket();
        }
        
        // Listen for page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.socket && !this.socket.connected) {
                this.socket.connect();
            }
        });

        // Handle Back/Forward Cache (bfcache)
        window.addEventListener('pageshow', (event) => {
            if (event.persisted) {
                 // Page was restored from cache, clear any stale notifications
                 const staleNotifications = document.querySelectorAll('.notification');
                 staleNotifications.forEach(n => n.remove());
                 // Ensure serverFlashMessages is empty so we don't re-render old flashes
                 window.serverFlashMessages = [];
            }
        });
    }
    
    createContainer() {
        // Remove any existing containers
        const existing = document.querySelectorAll('.notification-container, .flash-container');
        existing.forEach(el => el.remove());
        
        // Create single unified container
        this.container = document.createElement('div');
        this.container.className = 'notification-container';
        this.container.setAttribute('aria-live', 'polite');
        this.container.setAttribute('aria-atomic', 'false');
        document.body.appendChild(this.container);
    }
    
    handleServerFlashMessages() {
        // Handle flash messages from server data (prevents persistence)
        if (window.serverFlashMessages && window.serverFlashMessages.length > 0) {
            console.log('📬 Processing server flash messages:', window.serverFlashMessages);
            
            window.serverFlashMessages.forEach((flashData, index) => {
                const notificationData = {
                    id: `server-flash-${Date.now()}-${index}`,
                    type: flashData.type,
                    message: flashData.message,
                    created_at: flashData.timestamp,
                    auto_dismiss: true
                };
                
                // Slight delay to ensure DOM is ready
                setTimeout(() => {
                    this.showNotification(notificationData, true);
                }, index * 100);
            });
            
            // Clear the data to prevent re-processing
            window.serverFlashMessages = [];
        }
    }
    
    initSocket() {
        console.log('🔗 Connecting to Socket.IO...');
        this.socket = io({
            transports: ['websocket', 'polling'],
            upgrade: true,
            rememberUpgrade: true
        });
        
        // Connection events
        this.socket.on('connect', () => {
            console.log('✅ Socket.IO connected, ID:', this.socket.id);
            this.socket.emit('get_unread_notifications');
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('🔌 Socket.IO disconnected:', reason);
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('❌ Socket.IO connection error:', error);
        });
        
        // Notification events
        this.socket.on('new_notification', (data) => {
            console.log('📬 Received real-time notification:', data);
            this.showNotification(data, true);
        });
        
        this.socket.on('unread_notifications', (data) => {
            console.log('📫 Received unread notifications:', data.notifications?.length || 0);
            if (data.notifications) {
                data.notifications.forEach(notif => {
                    this.showNotification(notif, false); // Don't auto-dismiss existing
                });
            }
        });
        
        this.socket.on('notification_removed', (data) => {
            console.log('🗑️ Notification removed:', data.id);
            this.removeNotification(data.id);
        });
    }
    
    showNotification(data, autoFadeIn = true) {
        if (this.notifications.has(data.id)) {
            console.log('⚠️ Notification already exists:', data.id);
            return;
        }
        
        console.log('📝 Creating notification:', data);
        
        const notification = this.createNotificationElement(data);
        this.notifications.set(data.id, notification);
        
        // Add to container
        this.container.appendChild(notification);
        
        // Trigger entrance animation
        if (autoFadeIn) {
            requestAnimationFrame(() => {
                notification.classList.add('show');
            });
        } else {
            notification.classList.add('show');
        }
        
        // Auto-dismiss if enabled
        if (data.auto_dismiss !== false && autoFadeIn) {
            this.scheduleAutoDismiss(data.id, 6000); // 6 seconds
        }
    }
    
    createNotificationElement(data) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${data.type}`;
        notification.setAttribute('role', 'alert');
        notification.setAttribute('aria-live', 'assertive');
        notification.dataset.notificationId = data.id;
        
        const icon = this.getNotificationIcon(data.type);
        const timestamp = this.formatTimestamp(data.created_at);
        
        let actionsHtml = '';
        if (data.action_type && data.action_data) {
            actionsHtml = this.generateActionButtons(data.action_type, data.action_data);
        }
        
        notification.innerHTML = `
            <div class="notification-timer-bar"></div>
            <div class="notification-content">
                <div class="notification-icon">
                    ${icon}
                </div>
                <div class="notification-body">
                    <div class="notification-message">${this.escapeHtml(data.message)}</div>
                    <div class="notification-timestamp">${timestamp}</div>
                    ${actionsHtml}
                </div>
                <button class="notification-close" aria-label="Dismiss notification" data-action="close">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
        `;
        
        // Add event listeners
        this.addNotificationEventListeners(notification, data);
        
        return notification;
    }
    
    addNotificationEventListeners(notification, data) {
        // Close button
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeNotification(data.id);
        });
        
        // Action buttons
        const actionBtns = notification.querySelectorAll('.notification-action');
        actionBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleNotificationAction(data, btn.dataset.action);
            });
        });
    }
    
    scheduleAutoDismiss(notificationId, duration) {
        const notification = this.notifications.get(notificationId);
        if (!notification) return;
        
        console.log('⏱️ Scheduling auto-dismiss for:', notificationId, 'duration:', duration + 'ms');
        
        const timerBar = notification.querySelector('.notification-timer-bar');
        
        if (timerBar) {
            // Set initial state
            timerBar.style.transform = 'scaleX(1)';
            timerBar.style.transition = 'none';
            
            // Force reflow
            void timerBar.offsetWidth;
            
            // Start animation
            setTimeout(() => {
                timerBar.style.transition = `transform ${duration}ms linear`;
                timerBar.style.transform = 'scaleX(0)';
            }, 10);
        }
        
        // Schedule removal and track timer
        const timerId = setTimeout(() => {
            console.log('⏰ Auto-dismissing notification:', notificationId);
            this.removeNotification(notificationId);
        }, duration);
        
        this.timers.set(notificationId, timerId);
    }
    
    removeNotification(notificationId) {
        const notification = this.notifications.get(notificationId);
        if (!notification) {
            console.log('⚠️ Notification not found for removal:', notificationId);
            return;
        }
        
        console.log('🗑️ Removing notification:', notificationId);

        // Mark as read on server to prevent reappearance
        if (window.isAuthenticated && this.socket && this.socket.connected) {
            // Check if it's a server-side notification (integer ID)
            // Manual IDs are strings like "manual-...", server flash are "server-flash-..."
            const idStr = String(notificationId);
            if (!idStr.startsWith('manual-') && !idStr.startsWith('server-flash-')) {
                console.log('📤 Marking notification as read on server:', notificationId);
                this.socket.emit('mark_notification_read', { notification_id: notificationId });
            }
        }
        
        // Clear any active timer
        const timerId = this.timers.get(notificationId);
        if (timerId) {
            clearTimeout(timerId);
            this.timers.delete(notificationId);
        }
        
        // Hide notification
        notification.classList.remove('show');
        notification.classList.add('hide');
        
        // Remove from DOM after animation
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            this.notifications.delete(notificationId);
            console.log('✅ Notification removed from DOM:', notificationId);
        }, 300);
    }
    
    // Public API for programmatic notifications
    show(type, message, options = {}) {
        const notificationData = {
            id: `manual-${Date.now()}-${++this.notificationCount}`,
            type: type,
            message: message,
            created_at: new Date().toISOString(),
            auto_dismiss: options.autoDismiss !== false,
            ...options
        };
        
        this.showNotification(notificationData, true);
        return notificationData.id;
    }
    
    success(message, options = {}) {
        return this.show('success', message, options);
    }
    
    error(message, options = {}) {
        return this.show('error', message, { autoDismiss: false, ...options });
    }
    
    warning(message, options = {}) {
        return this.show('warning', message, options);
    }
    
    info(message, options = {}) {
        return this.show('info', message, options);
    }
    
    // Utility methods
    getNotificationIcon(type) {
        const icons = {
            success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4" /><circle cx="12" cy="12" r="10" /></svg>',
            error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M15 9l-6 6" /><path d="M9 9l6 6" /></svg>',
            warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>',
            info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" /></svg>',
            attendance: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>',
            enrollment: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" ry="1" /></svg>',
            query: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>',
            assignment: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14,2 14,8 20,8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10,9 9,9 8,9" /></svg>'
        };
        return icons[type] || icons.info;
    }
    
    formatTimestamp(timestamp) {
        if (!timestamp) return 'Just now';
        
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    generateActionButtons(actionType, actionData) {
        if (!actionType || !actionData) return '';
        
        let actionsHtml = '<div class="notification-actions">';
        
        switch (actionType) {
            case 'query':
                actionsHtml += `<button class="notification-action" data-action="view_query" style="background: oklch(50% 0.1 240); color: white;">View Query</button>`;
                break;
            case 'attendance':
                actionsHtml += `<button class="notification-action" data-action="view_attendance" style="background: oklch(50% 0.1 145); color: white;">View Details</button>`;
                break;
            case 'enrollment':
                actionsHtml += `<button class="notification-action" data-action="view_enrollment" style="background: oklch(50% 0.1 240); color: white;">Review</button>`;
                break;
        }
        
        actionsHtml += '</div>';
        return actionsHtml;
    }
    
    handleNotificationAction(notificationData, action) {
        console.log('🎯 Handling notification action:', action, notificationData);
        
        switch (action) {
            case 'view_query':
                if (notificationData.action_data?.query_id) {
                    window.location.href = `/admin/queries?highlight=${notificationData.action_data.query_id}`;
                }
                break;
            case 'view_attendance':
                window.location.href = '/attendance';
                break;
            case 'view_enrollment':
                window.location.href = '/admin/enrollments';
                break;
            default:
                console.warn('Unknown action:', action);
        }
        
        // Mark as read if it has an ID
        if (this.socket && notificationData.id && typeof notificationData.id === 'number') {
            this.socket.emit('mark_notification_read', { notification_id: notificationData.id });
        }
        
        this.removeNotification(notificationData.id);
    }
}

// Initialize unified notification manager
let notificationManager;

// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        notificationManager = new UnifiedNotificationManager();
        window.notifications = notificationManager; // Global access
    });
} else {
    notificationManager = new UnifiedNotificationManager();
    window.notifications = notificationManager;
}

// Legacy flash message removal function (for any remaining references)
function removeFlashMessage(index) {
    if (window.notifications) {
        console.log('⚠️ Legacy removeFlashMessage called, handled by unified system');
    }
}