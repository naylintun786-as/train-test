import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import matplotlib.pyplot as plt
import torch.nn.init as init

# import cv2


class NeuralNetwork(nn.Module):
    def __init__(self):
        super(NeuralNetwork, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.conv4 = nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1)
        self.bn4 = nn.BatchNorm2d(256)
        self.fc1 = nn.Linear(256 * 1 * 1, 512)  # Adjusted for final spatial size of 1x1
        self.fc2 = nn.Linear(512, 10)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.7)  # Increased dropout
        self.initialize_weights()

    def initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                init.normal_(m.weight, 0, 0.01)
                init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.pool(self.relu(self.bn1(self.conv1(x))))
        x = self.pool(self.relu(self.bn2(self.conv2(x))))
        x = self.pool(self.relu(self.bn3(self.conv3(x))))
        x = self.pool(self.relu(self.bn4(self.conv4(x))))

        # Dynamically calculate the number of features
        batch_size = x.size(0)
        num_features = x.size(1) * x.size(2) * x.size(3)
        x = x.view(batch_size, -1)  # Flatten the tensor

        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x


# Load the trained model
model = NeuralNetwork()
print(model)
model.load_state_dict(torch.load("model.pth"))  # Load your saved model
model.eval()  # Set the model to evaluation mode

# Define the class names for FashionMNIST
class_names = [
    "T-shirt/top",
    "Trouser",
    "Pullover",
    "Dress",
    "Coat",
    "Sandal",
    "Shirt",
    "Sneaker",
    "Bag",
    "Ankle boot",
]

# Define the image preprocessing pipeline
transform = transforms.Compose(
    [
        transforms.Grayscale(num_output_channels=1),  # Convert to grayscale
        transforms.Resize((28, 28)),  # Resize to 28x28
        transforms.ToTensor(),  # Convert to tensor
        transforms.Normalize((0.5,), (0.5,)),  # Normalize
    ]
)


# Load and preprocess the real image
def preprocess_image(image_path):
    image = Image.open(image_path)  # Open the image
    image = transform(image).unsqueeze(0)  # Add batch dimension
    return image


# Predict the class of the image
def predict_image(image_path, model):
    image = preprocess_image(image_path)
    with torch.no_grad():
        output = model(image)
        _, predicted = torch.max(output, 1)
        return class_names[predicted.item()]


# Example usage
image_path = "pullover.jpg"  # Replace with the path to your image
predicted_class = predict_image(image_path, model)
print(f"The predicted class is: {predicted_class}")

# Optional: Display the image


def display_image(image_path):
    image = Image.open(image_path)
    plt.imshow(image, cmap="gray")
    plt.title(f"Predicted: {predicted_class}")
    plt.axis("off")
    plt.show()


display_image(image_path)
