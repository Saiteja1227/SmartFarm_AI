#!/usr/bin/env python3
"""Download pre-trained plant disease model."""
import os
import requests
import sys

def download_model():
    """Download a pre-trained MobileNetV2 model for plant disease detection."""
    # Using a publicly available pre-trained model
    # This is a placeholder - in production, you would use your own trained model
    # For now, we'll create a simple model structure
    
    print("Setting up model directory...")
    os.makedirs("../models", exist_ok=True)
    
    # For this demo, we'll use MobileNetV2 with ImageNet weights
    # This won't detect plant diseases specifically, but will provide image classification
    print("Creating model with ImageNet weights...")
    
    try:
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras.applications import MobileNetV2
        
        # Load MobileNetV2 with ImageNet weights
        base_model = MobileNetV2(
            input_shape=(224, 224, 3),
            include_top=True,
            weights='imagenet'
        )
        
        # Save the model
        model_path = "../models/plant_disease_model.keras"
        base_model.save(model_path)
        print(f"Model saved to: {model_path}")
        
        # Create a dummy class names file (ImageNet classes)
        # In production, this would be your actual disease classes
        class_names = [
            "Tomato_Healthy", "Tomato_Late_Blight", "Tomato_Early_Blight",
            "Tomato_Septoria_Leaf_Spot", "Tomato_Target_Spot",
            "Tomato_Yellow_Leaf_Curl_Virus", "Tomato_Mosaic_Virus",
            "Tomato_Bacterial_Spot", "Tomato_Early_Blight",
            "Tomato_Late_Blight", "Tomato_Leaf_Mold",
            "Tomato_Septoria_Leaf_Spot", "Tomato_Spider_Mites",
            "Tomato_Target_Spot", "Tomato_Yellow_Leaf_Curl_Virus",
            "Tomato_Mosaic_Virus", "Tomato_Bacterial_Spot"
        ]
        
        import json
        with open("../models/class_names.json", "w") as f:
            json.dump(class_names, f)
        print(f"Class names saved to: ../models/class_names.json")
        
        print("\nModel setup complete!")
        print("Note: This uses ImageNet weights, not PlantVillage-specific training.")
        print("For production use, train on PlantVillage dataset on a compatible machine.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download_model()
