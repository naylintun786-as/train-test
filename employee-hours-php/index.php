<?php
require_once __DIR__ . '/config.php';

// Fetch employees with department name
$sql = "SELECT u.id, u.full_name, u.email, d.name AS department, u.hourly_rate, u.created_at
        FROM Users u
        LEFT JOIN Departments d ON d.id = u.department_id
        ORDER BY u.full_name";
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
    <div>
      <a class="btn btn-outline-light" href="add_shift.php">Add Shift</a>
    </div>
  </div>
</nav>
<div class="container">
  <div class="d-flex align-items-center justify-content-between mb-3">
    <h1 class="h3 m-0">Employees</h1>
  </div>
  <div class="table-responsive">
    <table class="table table-striped align-middle">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Department</th>
          <th>Hourly Rate</th>
          <th>Joined</th>
          <th style="width: 200px">Actions</th>
        </tr>
      </thead>
      <tbody>
      <?php while ($row = $result->fetch_assoc()): ?>
        <tr>
          <td><?= htmlspecialchars($row['full_name']) ?></td>
          <td><a href="mailto:<?= htmlspecialchars($row['email']) ?>"><?= htmlspecialchars($row['email']) ?></a></td>
          <td><?= htmlspecialchars($row['department'] ?: '—') ?></td>
          <td><?= $row['hourly_rate'] !== null ? '$' . number_format((float)$row['hourly_rate'], 2) : '—' ?></td>
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
