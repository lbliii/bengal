// Example TS entry (optional pipeline)
const ready = (fn: () => void) => {
  if (document.readyState !== 'loading') fn();
  else document.addEventListener('DOMContentLoaded', fn);
};

ready(() => {
  console.log('Bengal pipeline example JS loaded');
});
