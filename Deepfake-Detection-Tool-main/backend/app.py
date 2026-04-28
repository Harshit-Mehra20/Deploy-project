from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from PIL import Image
import os
import sys

# Make sure backend root is on the path so sub-packages resolve correctly
sys.path.insert(0, os.path.dirname(__file__))

from db.database import init_db
from routes.auth import auth_bp

app = Flask(__name__)

# Allow requests from:
#   - file:// pages  (browser sends Origin: null)
#   - any localhost port (dev)
CORS(app, resources={r"/*": {"origins": "*"}},
     supports_credentials=False)

# =========================
# REGISTER AUTH BLUEPRINT
# =========================
app.register_blueprint(auth_bp)

# =========================
# INITIALISE DATABASE
# =========================
init_db()

# =========================
# LAZY-LOAD TENSORFLOW
# TF is imported inside the route so a broken TF
# installation doesn't prevent Flask from starting.
# =========================
_model = None
_model_loaded = False

def _get_model():
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    try:
        import tensorflow as tf
        from tensorflow.keras.models import load_model

        model_path = os.path.join(os.path.dirname(__file__), "best_model.h5")
        if not os.path.exists(model_path):
            print(f"❌ Model file not found at: {model_path}")
            _model = None
            return _model

        # compile=False avoids optimizer-state errors when loading .h5 for inference only
        _model = load_model(model_path, compile=False)
        print(f"✅ best_model.h5 loaded successfully  (TF {tf.__version__})")
        print(f"   Input shape : {_model.input_shape}")
        print(f"   Output shape: {_model.output_shape}")
    except Exception as e:
        print(f"❌ Error loading best_model.h5: {e}")
        _model = None
    return _model

# =========================
# PREPROCESS IMAGE
# Must match training: MobileNetV2, 224×224, rescaled to [0,1]
# =========================
def preprocess_image(image):
    image = image.convert("RGB")
    image = image.resize((224, 224))          # same as training
    arr   = np.array(image, dtype=np.float32) / 255.0
    arr   = np.expand_dims(arr, axis=0)       # shape: (1, 224, 224, 3)
    return arr

# =========================
# PREDICTION FUNCTION
# =========================
def predict_image(image):
    model = _get_model()
    if model is None:
        return {"error": "Model not loaded. Check server logs."}

    processed  = preprocess_image(image)
    raw_output = float(model.predict(processed, verbose=0)[0][0])

    # MobileNetV2 trained with binary_crossentropy + sigmoid:
    #   output close to 0  → class 0 (first class alphabetically)
    #   output close to 1  → class 1 (second class alphabetically)
    # Assuming class mapping: 0 = fake / deepfake, 1 = real
    # (This matches typical DFDC / FaceForensics datasets ordered alphabetically)
    is_fake    = raw_output < 0.5
    confidence = (1 - raw_output) if is_fake else raw_output

    return {
        "result":     "Deepfake" if is_fake else "Real",
        "confidence": round(confidence * 100, 2),
        "raw_score":  round(raw_output, 4)
    }

# =========================
# HEALTH CHECK
# =========================
@app.route('/health', methods=['GET'])
def health():
    model_status = "loaded" if _model is not None else ("loading" if not _model_loaded else "failed")
    return jsonify({"status": "ok", "model": model_status})

# =========================
# DETECT API ROUTE
# =========================
@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded. Send a multipart/form-data request with field 'image'."}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "Empty filename — no file selected."}), 400

    try:
        image  = Image.open(file.stream)
        result = predict_image(image)
        print("Prediction result:", result)
        return jsonify(result)

    except Exception as e:
        print("❌ Prediction error:", e)
        return jsonify({"error": str(e)}), 500

# =========================
# RUN SERVER
# =========================
if __name__ == '__main__':
    print("🚀 DeepDetect backend starting on http://localhost:5000")
    print("   Loading best_model.h5 on first /predict request …")
    app.run(debug=True, host='0.0.0.0', port=5000)
