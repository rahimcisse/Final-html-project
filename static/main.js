// Load current user role and toggle visibility of elements with data-role-only
async function applyRoleVisibility() {
	try {
		const res = await fetch('/get_user');
		if (!res.ok) return; // not logged in or error
		const user = await res.json();
		const role = (user.role || '').toLowerCase();

		// Elements that should only be visible to a specific role
		document.querySelectorAll('[data-role-only]').forEach(el => {
			const allowed = el.getAttribute('data-role-only').split(',').map(s => s.trim().toLowerCase());
			if (!allowed.includes(role)) el.style.display = 'none';
			else el.style.display = '';
		});
	} catch (e) {
		// ignore - user may not be logged in
		console.debug('applyRoleVisibility:', e);
	}
}

window.addEventListener('DOMContentLoaded', applyRoleVisibility);
