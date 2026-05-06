function goBackSmart() {
    if (document.referrer && document.referrer.includes(window.location.origin)) {
        window.history.back();
    } else {
        window.location.href = "/services/";
    }
}