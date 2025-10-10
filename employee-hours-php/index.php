<?php
require_once __DIR__ . '/login.php';
require_once __DIR__ . '/config.php';

// Fetch users (minimal schema on shared host)
$sql = "SELECT id, user_name, created_at FROM time_stamp_users ORDER BY user_name";
$result = $mysqli->query($sql);
if (!$result) {
    http_response_code(500);
    echo 'Query error: ' . htmlspecialchars($mysqli->error);
    exit;
}
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Employees - Working Hours</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container">
    <a class="navbar-brand" href="index.php">Working Hours</a>
    <div class="d-flex gap-2 align-items-center">
      <span class="text-light small">Signed in as <strong><?= htmlspecialchars($_SESSION['user_name'] ?? 'unknown') ?></strong></span>
      <a class="btn btn-outline-light btn-sm" href="add_shift.php">Add Shift</a>
      <a class="btn btn-warning btn-sm" href="logout.php">Logout</a>
    </div>
  </div>
</nav>
<div class="container">
  <div class="d-flex align-items-center justify-content-between mb-3">
    <h1 class="h3 m-0">Users</h1>
  </div>
  <div class="table-responsive">
    <table class="table table-striped align-middle">
      <thead>
        <tr>
          <th>Username</th>
          <th>Joined</th>
          <th style="width: 200px">Actions</th>
        </tr>
      </thead>
      <tbody>
      <?php while ($row = $result->fetch_assoc()): ?>
        <tr>
          <td><?= htmlspecialchars($row['user_name']) ?></td>
          <td><?= htmlspecialchars(date('Y-m-d', strtotime($row['created_at']))) ?></td>
          <td>
            <a class="btn btn-sm btn-primary" href="shifts.php?user_id=<?= (int)$row['id'] ?>">View Shifts</a>
            <a class="btn btn-sm btn-success" href="add_shift.php?user_id=<?= (int)$row['id'] ?>">Add Shift</a>
          </td>
        </tr>
      <?php endwhile; ?>
      </tbody>
    </table>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
