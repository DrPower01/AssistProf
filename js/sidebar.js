document.addEventListener('DOMContentLoaded', function() {
  // Add active class to current page nav item
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.sidebar .nav-link');
  
  navLinks.forEach(link => {
    const linkPath = link.getAttribute('href');
    if (currentPath.includes(linkPath) && linkPath !== '/') {
      link.classList.add('active');
    } else if (currentPath === '/' && linkPath === '/') {
      link.classList.add('active');
    }
  });
  
  // Toggle sidebar collapse on mobile
  const toggleSidebarBtn = document.getElementById('toggleSidebar');
  const sidebar = document.querySelector('.sidebar');
  
  if (toggleSidebarBtn) {
    toggleSidebarBtn.addEventListener('click', function() {
      sidebar.classList.toggle('collapsed');
    });
  }
  
  // Add smooth transition when hovering nav items
  navLinks.forEach(link => {
    link.addEventListener('mouseenter', function() {
      this.style.transition = 'all 0.2s ease-in-out';
    });
  });
  
  // Responsive behavior - auto collapse on small screens
  function handleResize() {
    if (window.innerWidth < 768) {
      sidebar.classList.add('collapsed');
    } else {
      sidebar.classList.remove('collapsed');
    }
  }
  
  // Initial check and event listener for resize
  handleResize();
  window.addEventListener('resize', handleResize);
});
