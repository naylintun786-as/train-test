<?php
require_once __DIR__ . '/login.php';
require_once __DIR__ . '/config.php';

function fetchAllUsers(mysqli $mysqli): array {
    $users = [];
    $res = $mysqli->query("SELECT id, user_name FROM time_stamp_users ORDER BY user_name");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $users[] = $row;
        }
        $res->free();
    }
    return $users;
}

$users = fetchAllUsers($mysqli);

$selectedUserId = isset($_GET['user_id']) ? (int)$_GET['user_id'] : 0;
$errors = [];
$successMessage = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $userId = isset($_POST['user_id']) ? (int)$_POST['user_id'] : 0;
    $workDate = trim($_POST['work_date'] ?? '');
    $startTime = trim($_POST['start_time'] ?? '');
    $endTime = trim($_POST['end_time'] ?? '');
    $notes = trim($_POST['notes'] ?? '');

    // Basic validation
    if ($userId <= 0) {
        $errors[] = 'Please select an employee.';
    }

    if (!$workDate || !preg_match('/^\d{4}-\d{2}-\d{2}$/', $workDate)) {
        $errors[] = 'Please provide a valid date (YYYY-MM-DD).';
    }

    if (!$startTime || !preg_match('/^\d{2}:\d{2}$/', $startTime)) {
        $errors[] = 'Please provide a valid start time (HH:MM).';
    }

    if (!$endTime || !preg_match('/^\d{2}:\d{2}$/', $endTime)) {
        $errors[] = 'Please provide a valid end time (HH:MM).';
    }

    // Compare times (no overnight support in this simple version)
    if (!$errors) {
        $start = DateTime::createFromFormat('H:i', $startTime);
        $end = DateTime::createFromFormat('H:i', $endTime);
        if (!$start || !$end) {
            $errors[] = 'Invalid time format.';
        } elseif ($end <= $start) {
            $errors[] = 'End time must be after start time.';
        }
    }

    // Verify user exists
    if (!$errors && $userId > 0) {
        $stmt = $mysqli->prepare('SELECT id FROM time_stamp_users WHERE id = ?');
        $stmt->bind_param('i', $userId);
        $stmt->execute();
        $stmt->store_result();
        if ($stmt->num_rows === 0) {
            $errors[] = 'Selected employee does not exist.';
        }
        $stmt->close();
    }

    if (!$errors) {
        $stmt = $mysqli->prepare('INSERT INTO time_stamp_shifts (user_id, work_date, start_time, end_time, notes) VALUES (?, ?, ?, ?, ?)');
        $stmt->bind_param('issss', $userId, $workDate, $startTime, $endTime, $notes);
        if ($stmt->execute()) {
            // Fetch computed hours for confirmation (from generated column)
            $insertedId = $stmt->insert_id;
            $stmt->close();
            $stmt2 = $mysqli->prepare('SELECT total_hours FROM time_stamp_shifts WHERE id = ?');
            $stmt2->bind_param('i', $insertedId);
            $stmt2->execute();
            $stmt2->bind_result($totalHours);
            $stmt2->fetch();
            $stmt2->close();

            $successMessage = 'Shift added successfully. Total hours: ' . number_format((float)($totalHours ?? 0), 2);
            // Set selected user to the one we just posted for convenience
            $selectedUserId = $userId;
            // Reset POST fields
            $_POST = [];
        } else {
            $errors[] = 'Failed to add shift: ' . htmlspecialchars($stmt->error);
            $stmt->close();
        }
    }
}
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Add Shift</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container">
    <a class="navbar-brand" href="index.php">Working Hours</a>
    <div class="d-flex gap-2 align-items-center">
      <span class="text-light small">Signed in as <strong><?= htmlspecialchars($_SESSION['user_name'] ?? 'unknown') ?></strong></span>
      <a class="btn btn-outline-light btn-sm" href="shifts.php<?= $selectedUserId ? ('?user_id=' . (int)$selectedUserId) : '' ?>">View Shifts</a>
      <a class="btn btn-warning btn-sm" href="logout.php">Logout</a>
    </div>
  </div>
</nav>
<div class="container" style="max-width: 760px;">
  <h1 class="h3 mb-3">Add Work Shift</h1>

  <?php if ($successMessage): ?>
    <div class="alert alert-success"><?= htmlspecialchars($successMessage) ?></div>
  <?php endif; ?>

  <?php if ($errors): ?>
    <div class="alert alert-danger">
      <ul class="mb-0">
        <?php foreach ($errors as $e): ?>
          <li><?= htmlspecialchars($e) ?></li>
        <?php endforeach; ?>
      </ul>
    </div>
  <?php endif; ?>

  <form method="post" class="needs-validation" novalidate>
    <div class="mb-3">
      <label for="user_id" class="form-label">Employee</label>
      <select class="form-select" id="user_id" name="user_id" required>
        <option value="">Select employee...</option>
        <?php foreach ($users as $u): ?>
          <option value="<?= (int)$u['id'] ?>" <?= $selectedUserId === (int)$u['id'] ? 'selected' : '' ?>><?= htmlspecialchars($u['user_name']) ?></option>
        <?php endforeach; ?>
      </select>
      <div class="invalid-feedback">Please select an employee.</div>
    </div>

    <div class="row g-3">
      <div class="col-md-4">
        <label for="work_date" class="form-label">Date</label>
        <input type="date" class="form-control" id="work_date" name="work_date" value="<?= htmlspecialchars($_POST['work_date'] ?? '') ?>" required>
        <div class="invalid-feedback">Please provide a date.</div>
      </div>
      <div class="col-md-4">
        <label for="start_time" class="form-label">Start Time</label>
        <input type="time" class="form-control" id="start_time" name="start_time" value="<?= htmlspecialchars($_POST['start_time'] ?? '') ?>" required>
        <div class="invalid-feedback">Please provide a start time.</div>
      </div>
      <div class="col-md-4">
        <label for="end_time" class="form-label">End Time</label>
        <input type="time" class="form-control" id="end_time" name="end_time" value="<?= htmlspecialchars($_POST['end_time'] ?? '') ?>" required>
        <div class="invalid-feedback">Please provide an end time.</div>
      </div>
    </div>

    <div class="mb-3 mt-3">
      <label for="notes" class="form-label">Notes (optional)</label>
      <textarea class="form-control" id="notes" name="notes" rows="3" maxlength="500"><?= htmlspecialchars($_POST['notes'] ?? '') ?></textarea>
    </div>

    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-primary">Save Shift</button>
      <?php if ($selectedUserId): ?>
        <a class="btn btn-outline-secondary" href="shifts.php?user_id=<?= (int)$selectedUserId ?>">Back to Shifts</a>
      <?php else: ?>
        <a class="btn btn-outline-secondary" href="index.php">Back</a>
      <?php endif; ?>
    </div>
  </form>
</div>
<script>
// Bootstrap validation
(() => {
  'use strict';
  const forms = document.querySelectorAll('.needs-validation');
  Array.from(forms).forEach(form => {
    form.addEventListener('submit', event => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    }, false);
  });
})();
</script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
