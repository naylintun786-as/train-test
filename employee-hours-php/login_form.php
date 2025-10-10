<?php
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}
require_once __DIR__ . '/config.php';

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $userName = trim($_POST['user_name'] ?? '');
    if ($userName === '') {
        $error = 'Please enter a username.';
    } else {
        // Find existing user or create
        $stmt = $mysqli->prepare('SELECT id FROM time_stamp_users WHERE user_name = ?');
        $stmt->bind_param('s', $userName);
        $stmt->execute();
        $stmt->bind_result($userId);
        if ($stmt->fetch()) {
            $stmt->close();
        } else {
            $stmt->close();
            $stmt2 = $mysqli->prepare('INSERT INTO time_stamp_users (user_name) VALUES (?)');
            $stmt2->bind_param('s', $userName);
            if ($stmt2->execute()) {
                $userId = $stmt2->insert_id;
                $stmt2->close();
            } else {
                $error = 'Could not create user.';
            }
        }

        if (!$error && isset($userId)) {
            $_SESSION['user_id'] = (int)$userId;
            $_SESSION['user_name'] = $userName;
            $_SESSION['login_time'] = time();
            header('Location: index.php');
            exit;
        }
    }
}
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Login</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container" style="max-width: 480px;">
  <div class="card mt-5 shadow-sm">
    <div class="card-body">
      <h1 class="h4 mb-3">Sign in</h1>
      <?php if (isset($_GET['expired'])): ?>
        <div class="alert alert-warning">Your session expired. Please sign in again.</div>
      <?php endif; ?>
      <?php if ($error): ?>
        <div class="alert alert-danger"><?= htmlspecialchars($error) ?></div>
      <?php endif; ?>
      <form method="post" class="needs-validation" novalidate>
        <div class="mb-3">
          <label for="user_name" class="form-label">Username</label>
          <input type="text" class="form-control" id="user_name" name="user_name" required>
          <div class="invalid-feedback">Please enter your username.</div>
        </div>
        <button type="submit" class="btn btn-primary w-100">Sign in</button>
      </form>
    </div>
  </div>
</div>
<script>
(() => {
  const forms = document.querySelectorAll('.needs-validation');
  Array.from(forms).forEach(form => {
    form.addEventListener('submit', e => {
      if (!form.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
      }
      form.classList.add('was-validated');
    }, false);
  });
})();
</script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
