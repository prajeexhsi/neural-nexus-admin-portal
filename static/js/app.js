function toggleSidebar(){
  document.getElementById('sidebar')?.classList.toggle('open');
}
function confirmDelete(label){
  return window.confirm(`Delete this ${label}? This action cannot be undone.`);
}
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(el => el.classList.add('fade'));
}, 3500);
