<?php
// Minimal session guard; include this at the top of pages
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

// Session lifetime in seconds (example: 2 hours)
$SESSION_MAX_AGE_SECONDS = 7200;

if (!isset($_SESSION['user_id'])) {
    header('Location: login_form.php');
    exit;
}

if (!isset($_SESSION['login_time']) || (time() - (int)$_SESSION['login_time']) > $SESSION_MAX_AGE_SECONDS) {
    // Session expired
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000, $params['path'], $params['domain'], $params['secure'], $params['httponly']);
    }
    session_destroy();
    header('Location: login_form.php?expired=1');
    exit;
}

// Update last seen timestamp on every request
$_SESSION['last_seen'] = time();
?>
