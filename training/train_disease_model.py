#!/usr/bin/env python3
"""Train MobileNetV2 for plant disease detection using PlantVillage dataset."""
import os
import sys
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models, callbacks
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing import image_dataset_from_directory
import numpy as np

# Configuration
DATASET_URL = "https://github.com/spMohanty/PlantVillage-Dataset/archive/refs/heads/master.zip"
DATASET_DIR = "data/PlantVillage"
MODEL_SAVE_PATH = "../models/plant_disease_model.keras"
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 15
VALIDATION_SPLIT = 0.2

def download_dataset():
    """Download PlantVillage dataset."""
    import requests
    import zipfile
    
    print("Downloading PlantVillage dataset...")
    
    # Create data directory
    os.makedirs("data", exist_ok=True)
    
    # Download dataset
    zip_path = "data/plantvillage.zip"
    if not os.path.exists(zip_path):
        response = requests.get(DATASET_URL, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(zip_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = (downloaded / total_size) * 100 if total_size > 0 else 0
                    print(f"\rDownloading: {percent:.1f}%", end='')
        print("\nDownload complete!")
    
    # Extract dataset
    print("Extracting dataset...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall("data/")
    
    # Find the extracted directory
    extracted_dir = None
    for item in os.listdir("data"):
        if "PlantVillage" in item and os.path.isdir(os.path.join("data", item)):
            extracted_dir = os.path.join("data", item)
            break
    
    if extracted_dir:
        # Rename to standard location
        if os.path.exists(DATASET_DIR):
            import shutil
            shutil.rmtree(DATASET_DIR)
        os.rename(extracted_dir, DATASET_DIR)
        print(f"Dataset extracted to: {DATASET_DIR}")
    else:
        raise FileNotFoundError("Could not find extracted PlantVillage directory")
    
    # Clean up zip file
    os.remove(zip_path)
    print("Cleanup complete!")

def prepare_dataset():
    """Prepare train and validation datasets."""
    print("Preparing datasets...")
    
    # Use only color images (no grayscale)
    data_dir = os.path.join(DATASET_DIR, "PlantVillage-Dataset-master/color")
    
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Dataset directory not found: {data_dir}")
    
    train_ds = image_dataset_from_directory(
        data_dir,
        validation_split=VALIDATION_SPLIT,
        subset="training",
        seed=42,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        label_mode='categorical'
    )
    
    val_ds = image_dataset_from_directory(
        data_dir,
        validation_split=VALIDATION_SPLIT,
        subset="validation",
        seed=42,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        label_mode='categorical'
    )
    
    # Get class names
    class_names = train_ds.class_names
    print(f"Found {len(class_names)} disease classes")
    print(f"Classes: {class_names[:5]}...")  # Show first 5
    
    # Optimize dataset performance
    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.prefetch(buffer_size=AUTOTUNE)
    val_ds = val_ds.prefetch(buffer_size=AUTOTUNE)
    
    return train_ds, val_ds, class_names

def build_model(num_classes):
    """Build MobileNetV2 model with transfer learning."""
    print("Building MobileNetV2 model...")
    
    # Load pre-trained MobileNetV2
    base_model = MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights='imagenet'
    )
    
    # Freeze base layers
    base_model.trainable = False
    
    # Add custom classification head
    inputs = keras.Input(shape=(224, 224, 3))
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.2)(x)
    x = layers.Dense(512, activation='relu')(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    
    model = keras.Model(inputs, outputs)
    
    return model, base_model

def train_model(model, train_ds, val_ds):
    """Train the model with callbacks."""
    print("Starting training...")
    
    # Callbacks
    callbacks_list = [
        callbacks.EarlyStopping(
            monitor='val_loss',
            patience=3,
            restore_best_weights=True
        ),
        callbacks.ModelCheckpoint(
            MODEL_SAVE_PATH,
            monitor='val_accuracy',
            save_best_only=True,
            mode='max'
        ),
        callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.2,
            patience=2,
            min_lr=1e-6
        )
    ]
    
    # Compile model
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    # Train
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS,
        callbacks=callbacks_list,
        verbose=1
    )
    
    return history

def fine_tune(model, base_model, train_ds, val_ds):
    """Fine-tune the model by unfreezing some base layers."""
    print("Fine-tuning model...")
    
    # Unfreeze last few layers
    base_model.trainable = True
    for layer in base_model.layers[:-20]:
        layer.trainable = False
    
    # Recompile with lower learning rate
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    # Fine-tune
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=5,
        callbacks=[
            callbacks.EarlyStopping(patience=2, restore_best_weights=True),
            callbacks.ModelCheckpoint(MODEL_SAVE_PATH, monitor='val_accuracy', save_best_only=True)
        ],
        verbose=1
    )
    
    return history

def main():
    """Main training pipeline."""
    print("=" * 60)
    print("Plant Disease Detection Model Training")
    print("=" * 60)
    
    # Create models directory
    os.makedirs("../models", exist_ok=True)
    
    # Step 1: Download dataset
    if not os.path.exists(DATASET_DIR):
        download_dataset()
    else:
        print(f"Dataset already exists at: {DATASET_DIR}")
    
    # Step 2: Prepare datasets
    train_ds, val_ds, class_names = prepare_dataset()
    num_classes = len(class_names)
    
    # Save class names for inference
    import json
    with open("../models/class_names.json", "w") as f:
        json.dump(class_names, f)
    print(f"Saved class names to: ../models/class_names.json")
    
    # Step 3: Build model
    model, base_model = build_model(num_classes)
    model.summary()
    
    # Step 4: Train model
    history = train_model(model, train_ds, val_ds)
    
    # Step 5: Fine-tune
    history_fine = fine_tune(model, base_model, train_ds, val_ds)
    
    # Step 6: Save final model
    model.save(MODEL_SAVE_PATH)
    print(f"\nModel saved to: {MODEL_SAVE_PATH}")
    
    # Step 7: Evaluate
    print("\nFinal evaluation:")
    test_loss, test_acc = model.evaluate(val_ds)
    print(f"Validation accuracy: {test_acc:.2%}")
    
    print("\nTraining complete!")

if __name__ == "__main__":
    main()
