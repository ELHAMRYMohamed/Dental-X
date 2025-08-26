from ultralytics import YOLO
from flask import request, Flask, jsonify
from waitress import serve
from PIL import Image
import os
from PIL import Image, ImageDraw

app = Flask(__name__)

@app.route("/")
def root():
    """
    Site main page handler function.
    :return: Content of index.html file
    """
    with open("templates/index.html") as file:
        return file.read()


@app.route("/detect", methods=["POST"])
def detect():
    """
        Handler of /detect POST endpoint
        Receives uploaded file with a name "image_file", passes it
        through YOLOv8 object detection network and returns and array
        of bounding boxes.
        :return: a JSON array of objects bounding boxes in format [[x1,y1,x2,y2,object_type,probability],..]
    """
    try:
        print("Requête reçue sur /detect")
        
       
        if "image_file" not in request.files:
            print("Aucun fichier 'image_file' trouvé dans la requête")
            return jsonify({"error": "Aucun fichier fourni"}), 400
        
        buf = request.files["image_file"]
        
       
        if buf.filename == '':
            print("Nom de fichier vide")
            return jsonify({"error": "Fichier vide"}), 400
        
        print(f"Fichier reçu: {buf.filename}")
        
       
        result = detect_objects_on_image(buf.stream)
        
        print("Détection terminée avec succès")
        return jsonify(result)
        
    except Exception as e:
        print(f"Erreur dans l'endpoint /detect: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500


def detect_objects_on_image(buf):
    try:
        print("Début de la détection...")
        
        
        model = YOLO("model.pt")
        print("Modèle chargé avec succès")
        
       
        image = Image.open(buf)
        print(f"Image ouverte: {image.size}")
        
       
        results = model.predict(image)
        result = results[0]
        print(f"Prédiction terminée, {len(result.boxes) if result.boxes else 0} objets détectés")

        output = []
        class_images = {}
        
      
        if result.boxes is None or len(result.boxes) == 0:
            print("Aucune détection trouvée")
            return {"boxes": output, "class_images": class_images}
        
       
        if hasattr(result, 'orig_img'):
            img = Image.fromarray(result.orig_img) if not isinstance(result.orig_img, Image.Image) else result.orig_img
        else:
            img = image
        
        print(f"Image source préparée: {img.size}")

        
        boxes_by_class = {}
        for box in result.boxes:
            try:
                x1, y1, x2, y2 = [round(x) for x in box.xyxy[0].tolist()]
                class_id = int(box.cls[0].item())
                prob = round(box.conf[0].item(), 2)
                prob_percentage = f"{prob * 100:.2f}%"
                class_name = result.names[class_id]

                output.append([x1, y1, x2, y2, class_name, prob_percentage])

                if class_name not in boxes_by_class:
                    boxes_by_class[class_name] = []
                boxes_by_class[class_name].append((x1, y1, x2, y2, prob_percentage))
                
            except Exception as e:
                print(f"Erreur lors du traitement d'une box: {e}")
                continue

        print(f"Classes regroupées: {list(boxes_by_class.keys())}")

        
        os.makedirs("static/class_images", exist_ok=True)
        print("Dossier static/class_images créé")
        
        
        for class_name, boxes in boxes_by_class.items():
            try:
                print(f"Traitement de la classe: {class_name}")
                
               
                img_copy = img.copy()
                draw = ImageDraw.Draw(img_copy)
                
               
                for (x1, y1, x2, y2, conf) in boxes:
                   
                    colors = {
                        'Caries': 'red',
                        'Filling': 'blue', 
                        'Root Canal Treat': 'orange',
                        'default': 'green'
                    }
                    color = colors.get(class_name, colors['default'])
                    
                    
                    draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                    
                    
                    text = f"{class_name} ({conf})"
                    draw.text((x1, max(0, y1 - 20)), text, fill=color)
                
               
                safe_class_name = class_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                save_path = f"static/class_images/{safe_class_name}_only.jpg"
                
              
                img_copy.save(save_path, 'JPEG', quality=85)
                print(f"Image sauvegardée: {save_path}")
                
                
                detection_count = len(boxes)
                class_images[class_name] = {
                    "url": "/" + save_path,
                    "count": detection_count,
                    "detections": boxes
                }
                
            except Exception as e:
                print(f"Erreur lors de la création de l'image pour {class_name}: {e}")
                continue

        
        print(f"Classes détectées: {list(class_images.keys())}")
        for class_name, data in class_images.items():
            print(f"{class_name}: {data['count']} détections, image: {data['url']}")
        
        return {"boxes": output, "class_images": class_images}
        
    except Exception as e:
        print(f"Erreur dans detect_objects_on_image: {e}")
        import traceback
        traceback.print_exc()
       
        return {"boxes": [], "class_images": {}}


if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=8080)