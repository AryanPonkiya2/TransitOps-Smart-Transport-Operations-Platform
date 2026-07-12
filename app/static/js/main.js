document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Sidebar toggle logic on mobile devices
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebar.classList.toggle('show');
        });
        
        // Close sidebar when clicking outside of it on mobile
        document.addEventListener('click', function(e) {
            if (window.innerWidth < 992 && sidebar.classList.contains('show')) {
                if (!sidebar.contains(e.target) && e.target !== sidebarToggle) {
                    sidebar.classList.remove('show');
                }
            }
        });
    }

    // 2. Double-confirmation before destructive delete actions
    const deleteForms = document.querySelectorAll('form.confirm-delete');
    deleteForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const message = form.getAttribute('data-confirm-message') || "Are you absolutely sure you want to delete this record? This action cannot be undone.";
            if (!confirm(message)) {
                e.preventDefault(); // Stop submission
            }
        });
    });

    // 3. Auto-calculate total fuel cost on client-side for fuel forms
    const fuelQtyInput = document.getElementById('fuel_quantity');
    const fuelPriceInput = document.getElementById('fuel_price');
    const totalCostDisplay = document.getElementById('total_cost_display');

    if (fuelQtyInput && fuelPriceInput && totalCostDisplay) {
        function calculateFuelCost() {
            const qty = parseFloat(fuelQtyInput.value) || 0;
            const price = parseFloat(fuelPriceInput.value) || 0;
            const total = qty * price;
            totalCostDisplay.textContent = '₹' + total.toFixed(2);
        }
        fuelQtyInput.addEventListener('input', calculateFuelCost);
        fuelPriceInput.addEventListener('input', calculateFuelCost);
    }

    // 3.1 Auto-populate vehicle when selecting a linked trip in fuel forms
    const tripSelect = document.getElementById('trip_id');
    const vehicleSelect = document.getElementById('vehicle_id');
    if (tripSelect && vehicleSelect) {
        tripSelect.addEventListener('change', function() {
            const tripId = this.value;
            if (tripId && tripId !== '0') {
                fetch(`/trips/api/${tripId}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.vehicle_id) {
                            vehicleSelect.value = data.vehicle_id;
                        }
                    })
                    .catch(err => console.error("Error fetching trip vehicle:", err));
            }
        });
    }

    // 4. Highlight current sidebar menu link based on current path
    const currentPath = window.location.pathname;
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(function(link) {
        const href = link.getAttribute('href');
        if (href) {
            if (href === '/' && currentPath === '/') {
                link.parentElement.classList.add('active');
            } else if (href !== '/' && currentPath.startsWith(href)) {
                link.parentElement.classList.add('active');
            }
        }
    });

    // 5. Notifications Drawer fetching & polling
    const notificationBadge = document.getElementById('notificationBadge');
    const notificationList = document.getElementById('notificationList');
    
    function loadNotifications() {
        if (!notificationList || !notificationBadge) return;
        
        fetch('/notifications/api/recent')
            .then(response => {
                if (response.status === 401) return null; // Not logged in
                return response.json();
            })
            .then(data => {
                if (!data) return;
                const count = data.unread_count;
                if (count > 0) {
                    notificationBadge.textContent = count;
                    notificationBadge.classList.remove('d-none');
                } else {
                    notificationBadge.classList.add('d-none');
                }
                
                if (data.notifications.length === 0) {
                    notificationList.innerHTML = '<div class="p-3 text-center text-muted" style="font-size: 0.85rem;">No notifications found</div>';
                } else {
                    let html = '';
                    data.notifications.forEach(n => {
                        const unreadStyle = n.is_read ? '' : 'background-color: rgba(37, 99, 235, 0.05); font-weight: 500;';
                        const categoryColor = n.category === 'success' ? 'success' : (n.category === 'danger' ? 'danger' : (n.category === 'warning' ? 'warning' : 'primary'));
                        html += `
                            <div class="list-group-item list-group-item-action p-3 border-bottom" style="${unreadStyle} cursor: pointer;" onclick="markNotificationRead(${n.id}, this)">
                                <div class="d-flex w-100 justify-content-between align-items-center mb-1">
                                    <h6 class="mb-0 text-${categoryColor} fw-semibold" style="font-size: 0.85rem;">${n.title}</h6>
                                    <small class="text-muted" style="font-size: 0.7rem;">${n.created_at}</small>
                                </div>
                                <p class="mb-0 text-dark" style="font-size: 0.8rem; line-height: 1.3;">${n.message}</p>
                            </div>
                        `;
                    });
                    notificationList.innerHTML = html;
                }
            })
            .catch(err => console.error("Error loading notifications:", err));
    }
    
    if (notificationList && notificationBadge) {
        loadNotifications();
        // Poll every 20 seconds for real-time updates
        setInterval(loadNotifications, 20000);
    }
    
    // Global function to mark notification as read
    window.markNotificationRead = function(id, element) {
        const csrfTokenEl = document.querySelector('input[name="csrf_token"]');
        const token = csrfTokenEl ? csrfTokenEl.value : '';
        
        fetch(`/notifications/read/${id}`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': token,
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                element.style.backgroundColor = '';
                element.style.fontWeight = 'normal';
                loadNotifications();
            }
        })
        .catch(err => console.error("Error marking notification read:", err));
    }

});
