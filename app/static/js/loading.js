function showLoading() {
    document.querySelector('.submit-form').classList.add('hidden');
    document.querySelector('.loading-screen').classList.remove('hidden');

    let seconds = 0;
    setInterval(function() {
        seconds++;
        document.querySelector('.loading-timer').textContent = seconds + 's';
    }, 1000);
}