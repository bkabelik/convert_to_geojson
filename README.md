

batch converts intermaps json to geojson. python convert_to_multipoint.py input directory -o output directory
------------------------

"c:\OSGeo4W\bin\python-qgis.bat" create_heatmap_cli.py -i e:\saison_geojson_output -o e:\saison_geojson_output\output -r 0.0017966 -p 0.00017966
----------------


'''
import os
from qgis.core import (
    QgsRasterLayer, 
    QgsProject, 
    QgsCoordinateReferenceSystem, 
    QgsRasterFileWriter, 
    QgsRasterBandStats,
    QgsColorRampShader,
    QgsSingleBandPseudoColorRenderer,
    QgsRasterShader,
    QgsStyle
)

# --- CONFIGURATION ---
input_folder = r'C:\Path\To\Your\Input\Tiffs'  # Folder with your .tif files
output_folder = r'C:\Path\To\Your\Output'      # Folder for exported images
resolution = 0.00017966                        # As per your first screenshot
target_crs_authid = 'EPSG:4326'

# Export Compression Settings
create_options = [
    "COMPRESS=DEFLATE",
    "PREDICTOR=2",
    "ZLEVEL=9"
]

def apply_turbo_symbology(layer):
    """Applies Singleband Pseudocolor with Turbo ramp to the layer"""
    provider = layer.dataProvider()
    # Get statistics for Band 1 to find the max value
    stats = provider.bandStatistics(1, QgsRasterBandStats.All)
    
    min_val = 0.0000015  # As per your screenshot
    max_val = stats.maximumValue
    
    # Create the shader function
    shader = QgsColorRampShader()
    shader.setColorRampType(QgsColorRampShader.Interpolated)
    
    # Get the 'Turbo' ramp from QGIS style library
    style = QgsStyle.defaultStyle()
    turbo_ramp = style.colorRamp('Turbo') # Standard in modern QGIS
    
    # Generate 255 classes (standard for continuous)
    items = []
    num_classes = 255
    for i in range(num_classes + 1):
        # Calculate value at this step
        val = min_val + (max_val - min_val) * (i / num_classes)
        # Get color from Turbo ramp (0.0 to 1.0)
        color = turbo_ramp.color(i / num_classes)
        items.append(QgsColorRampShader.ColorRampItem(val, color, f"{val:.4f}"))
    
    shader.setColorRampItemList(items)
    
    # Apply shader to renderer
    raster_shader = QgsRasterShader()
    raster_shader.setRasterShaderFunction(shader)
    
    renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, raster_shader)
    layer.setRenderer(renderer)
    layer.triggerRepaint()

# --- MAIN LOOP ---
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

for filename in os.listdir(input_folder):
    if filename.lower().endswith(".tif"):
        file_path = os.path.join(input_folder, filename)
        base_name = os.path.splitext(filename)[0]
        
        # 1. Load Layer
        layer = QgsRasterLayer(file_path, base_name)
        if not layer.isValid():
            continue

        # 2. Apply Turbo Symbology
        apply_turbo_symbology(layer)
        print(f"Applied Turbo styling to {filename}")

        # 3. Setup Export
        output_path = os.path.join(output_folder, f"{base_name}_RGB.tif")
        crs = QgsCoordinateReferenceSystem(target_crs_authid)
        extent = layer.extent()
        
        # Calculate size based on your specific resolution
        width = int(extent.width() / resolution)
        height = int(extent.height() / resolution)

        # 4. Export as Rendered Image
        pipe = layer.pipe()
        writer = QgsRasterFileWriter(output_path)
        writer.setCreateOptions(create_options)
        
        error = writer.writeRaster(
            pipe,
            width,
            height,
            extent,
            crs
        )

        if error == QgsRasterFileWriter.NoError:
            print(f"Saved: {output_path}")
        else:
            print(f"Error saving {filename}: {error}")

print("Done!")
'''
