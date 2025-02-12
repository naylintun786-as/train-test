best_loss = float("inf")
patience = 3
epochs_without_improvement = 0

for epoch in range(epochs):
    train(train_dataloader, model, loss_fn, optimizer)
    val_loss = test(test_dataloader, model, loss_fn)

    if val_loss < best_loss:
        best_loss = val_loss
        epochs_without_improvement = 0
        torch.save(model.state_dict(), "best_model.pth")
    else:
        epochs_without_improvement += 1
        if epochs_without_improvement >= patience:
            print("Early stopping triggered.")
            break
