#!/usr/bin/env python3
"""
GPU test script for ML service.
"""

import torch
import time
from sentence_transformers import SentenceTransformer

def test_gpu():
    """Test GPU availability and performance."""
    print("🔍 Testing GPU availability...")

    # Check CUDA availability
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")

    if cuda_available:
        print(f"CUDA Device Count: {torch.cuda.device_count()}")
        print(f"Current Device: {torch.cuda.current_device()}")
        print(f"Device Name: {torch.cuda.get_device_name(0)}")
        print(f"Device Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

        # Test model loading on GPU
        print("\n🚀 Testing SentenceTransformer on GPU...")
        device = "cuda"
        model = SentenceTransformer("all-MiniLM-L6-v2")
        model = model.to(device)

        # Test embedding generation
        test_texts = [
            "This is a test article about artificial intelligence and machine learning.",
            "Breaking news: Scientists discover new method for renewable energy.",
            "Technology companies are investing heavily in quantum computing research."
        ]

        print(f"Generating embeddings for {len(test_texts)} texts...")

        # Time the embedding generation
        start_time = time.time()
        embeddings = model.encode(test_texts)
        end_time = time.time()

        print(f"✅ Generated {len(embeddings)} embeddings in {end_time - start_time:.2f} seconds")
        print(f"📊 Embedding shape: {embeddings.shape}")
        print(f"⚡ Speed: {len(test_texts) / (end_time - start_time):.1f} texts/second")

        # Check GPU memory usage
        print(f"\n💾 GPU Memory Usage:")
        print(f"  Allocated: {torch.cuda.memory_allocated(0) / 1024**2:.1f} MB")
        print(f"  Reserved: {torch.cuda.memory_reserved(0) / 1024**2:.1f} MB")

    else:
        print("❌ CUDA not available, falling back to CPU")
        device = "cpu"
        model = SentenceTransformer("all-MiniLM-L6-v2")

        test_texts = ["This is a test article about artificial intelligence."]
        start_time = time.time()
        embeddings = model.encode(test_texts)
        end_time = time.time()

        print(f"✅ Generated embedding on CPU in {end_time - start_time:.2f} seconds")
        print(f"📊 Embedding shape: {embeddings.shape}")

if __name__ == "__main__":
    test_gpu()
