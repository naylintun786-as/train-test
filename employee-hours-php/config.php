<?php
// Database configuration for MySQL (XAMPP default: user=root, pass="")
$DB_HOST = getenv('DB_HOST') ?: 'localhost';
$DB_NAME = getenv('DB_NAME') ?: 'employee_hours';
$DB_USER = getenv('DB_USER') ?: 'root';
$DB_PASS = getenv('DB_PASS') ?: '';
$DB_PORT = getenv('DB_PORT') ?: '3306';

$mysqli = @new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME, (int)$DB_PORT);
if ($mysqli->connect_errno) {
    http_response_code(500);
    echo '<!doctype html><html><head><meta charset="utf-8"><title>Database Error</title></head><body>';
    echo '<h1>Database connection failed</h1>';
    echo '<p>Please verify your database credentials in <code>config.php</code> and ensure MySQL is running.</p>';
    echo '<pre>' . htmlspecialchars($mysqli->connect_error) . '</pre>';
    echo '</body></html>';
    exit;
}

$mysqli->set_charset('utf8mb4');
?>
