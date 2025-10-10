<?php
require_once __DIR__ . '/config.php';

$userId = isset($_GET['user_id']) ? (int)$_GET['user_id'] : 0;
if ($userId <= 0) {
    header('Location: index.php');
    exit;
}

// Fetch user details
$stmt = $mysqli->prepare('SELECT u.full_name, u.email, d.name AS department FROM Users u LEFT JOIN Departments d ON d.id = u.department_id WHERE u.id = ?');
$stmt->bind_param('i', $userId);
$stmt->execute();
$user = $stmt->get_result()->fetch_assoc();
$stmt->close();

if (!$user) {
    http_response_code(404);
    echo 'User not found';
    exit;
}

// Fetch shifts
$stmt = $mysqli->prepare('SELECT id, work_date, start_time, end_time, notes, total_hours, created_at FROM Work_Shifts WHERE user_id = ? ORDER BY work_date DESC, start_time DESC');
$stmt->bind_param('i', $userId);
$stmt->execute();
$shiftsRes = $stmt->get_result();
$stmt->close();

// Summary (total hours)
$stmt = $mysqli->prepare('SELECT COALESCE(SUM(total_hours), 0) AS total_hours_sum FROM Work_Shifts WHERE user_id = ?');
$stmt->bind_param('i', $userId);
$stmt->execute();
$stmt->bind_result($totalHoursSum);
$stmt->fetch();
$stmt->close();
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><?= htmlspecialchars($user['full_name']) ?> - Shifts</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container">
    <a class="navbar-brand" href="index.php">Working Hours</a>
    <div>
      <a class="btn btn-success" href="add_shift.php?user_id=<?= $userId ?>">Add Shift</a>
    </div>
  </div>
</nav>
<div class="container">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <div>
      <h1 class="h3 mb-0">Shifts - <?= htmlspecialchars($user['full_name']) ?></h1>
      <div class="text-muted"><?= htmlspecialchars($user['email']) ?><?= $user['department'] ? ' · ' . htmlspecialchars($user['department']) : '' ?></div>
    </div>
    <div class="text-end">
      <div class="fw-semibold">Total Hours</div>
      <div class="display-6"><?= number_format((float)$totalHoursSum, 2) ?></div>
    </div>
  </div>

  <div class="table-responsive">
    <table class="table table-striped align-middle">
      <thead>
        <tr>
          <th>Date</th>
          <th>Start</th>
          <th>End</th>
          <th>Hours</th>
          <th>Notes</th>
          <th>Added</th>
        </tr>
      </thead>
      <tbody>
      <?php if ($shiftsRes->num_rows === 0): ?>
        <tr><td colspan="6" class="text-center text-muted">No shifts yet.</td></tr>
      <?php else: ?>
        <?php while ($s = $shiftsRes->fetch_assoc()): ?>
          <tr>
            <td><?= htmlspecialchars($s['work_date']) ?></td>
            <td><?= htmlspecialchars(substr($s['start_time'], 0, 5)) ?></td>
            <td><?= htmlspecialchars(substr($s['end_time'], 0, 5)) ?></td>
            <td><?= number_format((float)$s['total_hours'], 2) ?></td>
            <td><?= htmlspecialchars($s['notes'] ?? '') ?></td>
            <td><?= htmlspecialchars($s['created_at']) ?></td>
          </tr>
        <?php endwhile; ?>
      <?php endif; ?>
      </tbody>
    </table>
  </div>

  <a class="btn btn-outline-secondary" href="index.php">Back</a>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
