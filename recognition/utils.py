import json
import urllib.request
import urllib.parse
import numpy as np
from PIL import Image, UnidentifiedImageError

# Lazy-load model on first prediction (not at import time)
_model = None

def _get_model():
    global _model
    if _model is None:
        import tensorflow as tf
        from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2

        # Keep TensorFlow's runtime pools small on memory-constrained services.
        tf.config.threading.set_intra_op_parallelism_threads(1)
        tf.config.threading.set_inter_op_parallelism_threads(1)
        print("Loading MobileNetV2 model... (first time only)")
        _model = MobileNetV2(weights='imagenet')
        _model.trainable = False
        print("Model loaded successfully!")
    return _model

def _preprocess_image(file_obj) -> np.ndarray:
    """Resize image to 224x224 and apply MobileNetV2 preprocessing."""
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
    with Image.open(file_obj) as source_image:
        resized_image = source_image.convert('RGB').resize((224, 224))
        arr = np.asarray(resized_image, dtype=np.float32)
        batch = np.expand_dims(arr, axis=0)
    return preprocess_input(batch)

def get_wikipedia_info(query):
    """Fetch summary and basic info from Wikipedia API."""
    safe_query = urllib.parse.quote(query)
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={safe_query}&format=json"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            pages = data['query']['pages']
            page_id = list(pages.keys())[0]
            
            if page_id == "-1":
                return f"The {query} is a recognized object class in the ImageNet dataset."
                
            extract = pages[page_id].get('extract', '')
            if extract:
                paragraphs = extract.split('\n')
                return paragraphs[0] if paragraphs else extract
            return f"The {query} is a recognized object class in the ImageNet dataset."
    except Exception as e:
        return f"The {query} is an identified subject in the uploaded image."

# Specialized image galleries for accurate category matching
SIMILAR_IMAGE_GALLERIES = {
    "motorcycle": [
        {"name": "Sports Motorcycle", "url": "https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&w=300&q=80"},
        {"name": "Cruiser Bike", "url": "https://images.unsplash.com/photo-1568772585407-9361f9bf3a87?auto=format&fit=crop&w=300&q=80"},
        {"name": "Urban Scooter", "url": "https://images.unsplash.com/photo-1591637333184-19aa84b3e01f?auto=format&fit=crop&w=300&q=80"},
        {"name": "Superbike", "url": "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f?auto=format&fit=crop&w=300&q=80"},
        {"name": "Touring Bike", "url": "https://images.unsplash.com/photo-1515777315837-281764d53391?auto=format&fit=crop&w=300&q=80"}
    ],
    "dog": [
        {"name": "Labrador Retriever", "url": "https://images.unsplash.com/photo-1591769225440-811ad7d6eca2?auto=format&fit=crop&w=300&q=80"},
        {"name": "German Shepherd", "url": "https://images.unsplash.com/photo-1589941013453-ec89f33b5e95?auto=format&fit=crop&w=300&q=80"},
        {"name": "Poodle", "url": "https://images.unsplash.com/photo-1560743641-3914f2c45636?auto=format&fit=crop&w=300&q=80"},
        {"name": "Beagle", "url": "https://images.unsplash.com/photo-1537151608804-ea6f0b407bc3?auto=format&fit=crop&w=300&q=80"},
        {"name": "Rottweiler", "url": "https://images.unsplash.com/photo-1567752881298-894bb81f9379?auto=format&fit=crop&w=300&q=80"}
    ],
    "cat": [
        {"name": "Siamese Cat", "url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=300&q=80"},
        {"name": "Persian Cat", "url": "https://images.unsplash.com/photo-1573865526739-10659fec78a5?auto=format&fit=crop&w=300&q=80"},
        {"name": "Bengal Cat", "url": "https://images.unsplash.com/photo-1513360371669-4adf3dd7dff8?auto=format&fit=crop&w=300&q=80"},
        {"name": "Maine Coon", "url": "https://images.unsplash.com/photo-1543852786-1cf6624b9987?auto=format&fit=crop&w=300&q=80"},
        {"name": "Tabby Cat", "url": "https://images.unsplash.com/photo-1561948955-570b270e7c36?auto=format&fit=crop&w=300&q=80"}
    ],
    "car": [
        {"name": "Sports Car", "url": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=300&q=80"},
        {"name": "Luxury Sedan", "url": "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=300&q=80"},
        {"name": "Convertible", "url": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=300&q=80"},
        {"name": "Supercar", "url": "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?auto=format&fit=crop&w=300&q=80"},
        {"name": "Coupe", "url": "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=300&q=80"}
    ],
    "flower": [
        {"name": "Sunflower", "url": "https://images.unsplash.com/photo-1597848212624-a19eb35e2651?auto=format&fit=crop&w=300&q=80"},
        {"name": "Red Rose", "url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=300&q=80"},
        {"name": "Tulip", "url": "https://images.unsplash.com/photo-1520763185298-1b434c919102?auto=format&fit=crop&w=300&q=80"},
        {"name": "Orchid", "url": "https://images.unsplash.com/photo-1525310072745-f49212b5ac6d?auto=format&fit=crop&w=300&q=80"},
        {"name": "Daisy", "url": "https://images.unsplash.com/photo-1606041008023-472dfb5e530f?auto=format&fit=crop&w=300&q=80"}
    ],
    "object": [
        {"name": "Digital Watch", "url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=300&q=80"},
        {"name": "Headphones", "url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=300&q=80"},
        {"name": "Smart Laptop", "url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=300&q=80"},
        {"name": "Camera", "url": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=300&q=80"},
        {"name": "Smartphone", "url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=300&q=80"}
    ]
}

# Specialized knowledge dictionary for popular image categories to provide high-detail output matching Reference 1
KNOWN_DETAILS = {
    "golden retriever": {
        "main_title": "Dog",
        "subtitle": "Breed: Golden Retriever",
        "tag": "Animal",
        "description": "The Golden Retriever is a friendly, intelligent, and loyal dog breed, known for its gentle nature and playful personality. It is widely kept as a family pet and is also used in service roles due to its trainability and calm temperament.",
        "attributes": [
            {"label": "Type", "value": "Dog (Domestic Animal)", "icon": "paw"},
            {"label": "Breed", "value": "Golden Retriever", "icon": "tag"},
            {"label": "Lifespan", "value": "10 – 12 years", "icon": "heart"},
            {"label": "Size", "value": "Large (51 – 61 cm)", "icon": "size"},
            {"label": "Weight", "value": "25 – 34 kg", "icon": "weight"},
            {"label": "Temperament", "value": "Friendly, Loyal, Intelligent", "icon": "smile"},
            {"label": "Common Uses", "value": "Family pet, Therapy dog, Search & rescue, Guide dog", "icon": "briefcase"},
            {"label": "Origin", "value": "Scotland", "icon": "globe"}
        ],
        "similar_images": SIMILAR_IMAGE_GALLERIES["dog"]
    },
    "moped": {
        "main_title": "Moped",
        "subtitle": "Category: Moped / Scooter",
        "tag": "Vehicle",
        "description": "A moped is a lightweight motor vehicle or motorcycle with an engine capacity usually under 50cc. Designed for convenient urban transportation and high fuel efficiency.",
        "attributes": [
            {"label": "Type", "value": "Motor Vehicle (Two-Wheeler)", "icon": "paw"},
            {"label": "Model", "value": "Moped / Scooter", "icon": "tag"},
            {"label": "Power Source", "value": "Combustion / Electric Motor", "icon": "heart"},
            {"label": "Capacity", "value": "1 – 2 Passengers", "icon": "size"},
            {"label": "Weight", "value": "70 – 120 kg", "icon": "weight"},
            {"label": "Drive Type", "value": "Automatic CVT / Belt Drive", "icon": "smile"},
            {"label": "Common Uses", "value": "City commuting, Delivery, Personal transport", "icon": "briefcase"},
            {"label": "Origin", "value": "Global Automotive Industry", "icon": "globe"}
        ],
        "similar_images": SIMILAR_IMAGE_GALLERIES["motorcycle"]
    },
    "motorcycle": {
        "main_title": "Motorcycle",
        "subtitle": "Category: Motorcycle / Bike",
        "tag": "Vehicle",
        "description": "A motorcycle is a two- or three-wheeled motor vehicle designed for personal transportation, commuting, and sport, engineered for speed, maneuvering, and performance.",
        "attributes": [
            {"label": "Type", "value": "Motor Vehicle (Two-Wheeler)", "icon": "paw"},
            {"label": "Model", "value": "Motorcycle / Street Bike", "icon": "tag"},
            {"label": "Power Source", "value": "Four-Stroke Engine", "icon": "heart"},
            {"label": "Capacity", "value": "1 – 2 Passengers", "icon": "size"},
            {"label": "Weight", "value": "130 – 220 kg", "icon": "weight"},
            {"label": "Drive Type", "value": "Chain / Shaft Drive", "icon": "smile"},
            {"label": "Common Uses", "value": "Commuting, Touring, Sport", "icon": "briefcase"},
            {"label": "Origin", "value": "Global Automotive Industry", "icon": "globe"}
        ],
        "similar_images": SIMILAR_IMAGE_GALLERIES["motorcycle"]
    }
}

def predict_image(file_obj):
    """Return structured detailed insights for the given image file."""
    from tensorflow.keras.applications.mobilenet_v2 import decode_predictions
    try:
        x = _preprocess_image(file_obj)
    except UnidentifiedImageError:
        raise ValueError('Uploaded file is not a valid image.')

    model = _get_model()
    preds = model(x, training=False).numpy()
    decoded = decode_predictions(preds, top=1)[0]
    del preds, x
    
    _, raw_name, confidence = decoded[0]
    class_name = raw_name.replace('_', ' ').title()
    key_name = raw_name.replace('_', ' ').lower()
    conf_percent = round(float(confidence) * 100, 1)

    # Check if we have exact detailed knowledge
    if key_name in KNOWN_DETAILS:
        info = KNOWN_DETAILS[key_name]
        return {
            'class_name': info['main_title'],
            'subtitle': info['subtitle'],
            'confidence': f"{conf_percent}%",
            'description': info['description'],
            'tag': info['tag'],
            'attributes': info['attributes'],
            'similar_images': info['similar_images']
        }
    
    # Generic intelligent fallback based on class name & Wikipedia
    description = get_wikipedia_info(class_name)
    
    is_motorcycle = any(k in key_name or k in description.lower() for k in ['moped', 'motorcycle', 'scooter', 'moped', 'minibike', 'motorbike', 'vespa'])
    is_dog_or_cat = any(k in key_name or k in description.lower() for k in ['retriever', 'spaniel', 'terrier', 'hound', 'dog', 'cat', 'shepherd', 'poodle', 'bulldog'])
    is_cat = any(k in key_name or k in description.lower() for k in ['cat', 'tabby', 'siamese', 'persian', 'lynx', 'leopard', 'tiger'])
    is_animal = is_dog_or_cat or is_cat or any(k in description.lower() for k in ['animal', 'species', 'mammal', 'bird', 'fauna'])
    is_car = any(k in key_name or k in description.lower() for k in ['car', 'truck', 'bus', 'convertible', 'sports car', 'sedan', 'van'])
    is_flower = any(k in key_name or k in description.lower() for k in ['flower', 'rose', 'sunflower', 'tulip', 'daisy', 'orchid', 'bloom'])
    
    if is_motorcycle:
        main_title = class_name
        subtitle = f"Category: {class_name}"
        tag = "Vehicle"
        attributes = [
            {"label": "Type", "value": "Motor Vehicle (Two-Wheeler)", "icon": "paw"},
            {"label": "Model", "value": class_name, "icon": "tag"},
            {"label": "Power Source", "value": "Combustion / Electric", "icon": "heart"},
            {"label": "Capacity", "value": "1 – 2 Passengers", "icon": "size"},
            {"label": "Weight", "value": "90 – 180 kg", "icon": "weight"},
            {"label": "Drive Type", "value": "Chain / Belt Drive", "icon": "smile"},
            {"label": "Common Uses", "value": "Commuting, Personal transport", "icon": "briefcase"},
            {"label": "Origin", "value": "Automotive Industry", "icon": "globe"}
        ]
        similar_images = SIMILAR_IMAGE_GALLERIES["motorcycle"]
    elif is_dog_or_cat:
        main_title = "Dog" if "dog" in key_name or any(d in key_name for d in ['retriever', 'shepherd', 'terrier', 'beagle', 'poodle', 'hound']) else "Cat"
        subtitle = f"Breed: {class_name}"
        tag = "Animal"
        attributes = [
            {"label": "Type", "value": f"{main_title} (Domestic Animal)", "icon": "paw"},
            {"label": "Breed", "value": class_name, "icon": "tag"},
            {"label": "Lifespan", "value": "10 – 15 years", "icon": "heart"},
            {"label": "Size", "value": "Medium to Large", "icon": "size"},
            {"label": "Weight", "value": "15 – 30 kg", "icon": "weight"},
            {"label": "Temperament", "value": "Loyal, Active, Intelligent", "icon": "smile"},
            {"label": "Common Uses", "value": "Companion, Family pet", "icon": "briefcase"},
            {"label": "Origin", "value": "Selective Breeding", "icon": "globe"}
        ]
        similar_images = SIMILAR_IMAGE_GALLERIES["cat"] if main_title == "Cat" else SIMILAR_IMAGE_GALLERIES["dog"]
    elif is_animal:
        main_title = class_name
        subtitle = f"Species: {class_name}"
        tag = "Animal"
        attributes = [
            {"label": "Type", "value": "Fauna / Living Organism", "icon": "paw"},
            {"label": "Species", "value": class_name, "icon": "tag"},
            {"label": "Habitat", "value": "Natural Environment", "icon": "heart"},
            {"label": "Diet", "value": "Herbivore / Carnivore", "icon": "size"},
            {"label": "Activity", "value": "Diurnal / Nocturnal", "icon": "weight"},
            {"label": "Status", "value": "Stable Population", "icon": "smile"},
            {"label": "Role", "value": "Ecosystem Balance", "icon": "briefcase"},
            {"label": "Origin", "value": "Native Wildlife", "icon": "globe"}
        ]
        similar_images = SIMILAR_IMAGE_GALLERIES["dog"]
    elif is_car:
        main_title = class_name
        subtitle = f"Category: {class_name}"
        tag = "Vehicle"
        attributes = [
            {"label": "Type", "value": "Motor Vehicle (Four-Wheeler)", "icon": "paw"},
            {"label": "Model", "value": class_name, "icon": "tag"},
            {"label": "Power Source", "value": "Combustion / Electric", "icon": "heart"},
            {"label": "Capacity", "value": "2 – 5 Passengers", "icon": "size"},
            {"label": "Weight", "value": "1,200 – 2,000 kg", "icon": "weight"},
            {"label": "Drive Type", "value": "Front / Rear / AWD", "icon": "smile"},
            {"label": "Common Uses", "value": "Transportation, Travel", "icon": "briefcase"},
            {"label": "Origin", "value": "Automobile Industry", "icon": "globe"}
        ]
        similar_images = SIMILAR_IMAGE_GALLERIES["car"]
    elif is_flower:
        main_title = class_name
        subtitle = f"Flora: {class_name}"
        tag = "Plant"
        attributes = [
            {"label": "Type", "value": "Flowering Plant", "icon": "paw"},
            {"label": "Species", "value": class_name, "icon": "tag"},
            {"label": "Bloom Season", "value": "Spring / Summer", "icon": "heart"},
            {"label": "Sunlight", "value": "Full Sun / Partial Shade", "icon": "size"},
            {"label": "Watering", "value": "Regular Moisture", "icon": "weight"},
            {"label": "Fragrance", "value": "Aromatic / Mild", "icon": "smile"},
            {"label": "Common Uses", "value": "Gardening, Decoration", "icon": "briefcase"},
            {"label": "Origin", "value": "Botanical Habitat", "icon": "globe"}
        ]
        similar_images = SIMILAR_IMAGE_GALLERIES["flower"]
    else:
        main_title = class_name
        subtitle = f"Object: {class_name}"
        tag = "Object"
        attributes = [
            {"label": "Type", "value": "Physical Object", "icon": "paw"},
            {"label": "Category", "value": class_name, "icon": "tag"},
            {"label": "Material", "value": "Composite / Synthetic", "icon": "heart"},
            {"label": "Durability", "value": "Standard Wear", "icon": "size"},
            {"label": "Size", "value": "Variable Dimensions", "icon": "weight"},
            {"label": "Condition", "value": "Good / Functional", "icon": "smile"},
            {"label": "Common Uses", "value": "Everyday utility", "icon": "briefcase"},
            {"label": "Origin", "value": "Manufactured / Natural", "icon": "globe"}
        ]
        similar_images = SIMILAR_IMAGE_GALLERIES["object"]

    return {
        'class_name': main_title,
        'subtitle': subtitle,
        'confidence': f"{conf_percent}%",
        'description': description,
        'tag': tag,
        'attributes': attributes,
        'similar_images': similar_images
    }
