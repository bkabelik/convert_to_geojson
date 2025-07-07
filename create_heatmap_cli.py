# -*- coding: utf-8 -*-

"""
QGIS Heatmap Generation Script (Multi-Folder, Final Corrected Version)

Uses the correct algorithm ID, a compatible styling method, the correct
style saving method, and the correct 'PIXEL_SIZE' parameter for QGIS 3.34.
"""

import os
import sys
import argparse

# --- QGIS INSTALLATION PATH (IMPORTANT FOR STANDALONE EXECUTION) ---
QGIS_INSTALL_PATH = r'C:\OSGeo4W\apps\qgis'
# --- END OF IMPORTANT CONFIGURATION ---

# --- Global variables for QGIS objects ---
qgs_app = None
processing = None
QgsVectorLayer, QgsRasterLayer, QgsSingleBandPseudoColorRenderer = (None, None, None)
QgsColorRampShader, QgsStyle, QgsProcessingException, QgsRasterShader = (None, None, None, None)
QgsApplication = None


def init_qgis_app_standalone(qgis_install_path):
    """Initializes a QGIS application and imports all necessary modules."""
    
    global qgs_app, processing, QgsApplication
    global QgsVectorLayer, QgsRasterLayer, QgsSingleBandPseudoColorRenderer
    global QgsColorRampShader, QgsStyle, QgsProcessingException, QgsRasterShader
    
    from qgis.core import QgsApplication
    qgs_app = QgsApplication([], False)

    QgsApplication.setPrefixPath(qgis_install_path, True)
    print(f"QGIS prefix path set to: {QgsApplication.prefixPath()}")

    plugins_path = os.path.join(qgis_install_path, 'python', 'plugins')
    if plugins_path not in sys.path:
        sys.path.insert(0, plugins_path)
        print(f"Plugins path added: {plugins_path}")

    qgs_app.initQgis()
    
    try:
        import processing
        from processing.core.Processing import Processing
        Processing.initialize()
    except ImportError as e:
        print(f"\nCRITICAL ERROR: Could not import the 'processing' module. Details: {e}")
        sys.exit(1)

    from qgis.core import (
        QgsVectorLayer, QgsRasterLayer, QgsSingleBandPseudoColorRenderer,
        QgsColorRampShader, QgsStyle, QgsProcessingException, QgsRasterShader
    )
    
    alg_count = len(QgsApplication.processingRegistry().algorithms())
    
    if alg_count == 0:
        print("\nCRITICAL ERROR: No processing algorithms were loaded.")
        sys.exit(1)
    else:
        print(f"QGIS application and Processing framework initialized successfully ({alg_count} algorithms loaded).")

COLORMAP_NAME = 'Turbo'

def get_subdirectories(parent_dir):
    if not os.path.isdir(parent_dir):
        print(f"Error: Input directory not found: {parent_dir}")
        return []
    subdirs = [d.path for d in os.scandir(parent_dir) if d.is_dir()]
    print(f"Found {len(subdirs)} subdirectories to process in '{parent_dir}'.")
    return subdirs

def find_geojson_files(folder_path):
    geojson_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.geojson'):
                geojson_files.append(os.path.join(root, file))
    return geojson_files

def merge_geojson_to_memory_layer(geojson_files):
    if not geojson_files: return None
    first_layer = QgsVectorLayer(geojson_files[0], "temp_first", "ogr")
    if not first_layer.isValid():
        print(f"Error: Could not load first GeoJSON: {geojson_files[0]}")
        return None
    target_crs = first_layer.crs()
    print(f"  -> Using CRS: {target_crs.authid()}")
    if target_crs.isGeographic():
        print("  -> WARNING: Data is in Geographic CRS (lat/lon). Radius/pixel size are in degrees.")
    merged_layer = QgsVectorLayer(f"Point?crs={target_crs.authid()}", "merged_points", "memory")
    provider = merged_layer.dataProvider()
    merged_layer.startEditing()
    total_features = 0
    for f_path in geojson_files:
        layer = QgsVectorLayer(f_path, os.path.basename(f_path), "ogr")
        if not layer.isValid(): continue
        for feature in layer.getFeatures(): provider.addFeature(feature); total_features += 1
    merged_layer.commitChanges()
    merged_layer.updateExtents()
    print(f"  -> Merged {total_features} features from {len(geojson_files)} file(s).")
    return merged_layer

def create_heatmap(input_layer, output_path, radius, pixel_size):
    print("  -> Generating heatmap raster...")
    alg_id = "qgis:heatmapkerneldensityestimation"
    try:
        # --- THIS IS THE FIX ---
        # The 'qgis:' prefixed algorithm uses a single PIXEL_SIZE parameter.
        params = {
            'INPUT': input_layer,
            'RADIUS': radius,
            'PIXEL_SIZE': pixel_size,
            'OUTPUT': output_path
        }
        # -----------------------
        result = processing.run(alg_id, params)
        # Some versions of this older algorithm output to 'OUTPUT_RASTER'
        if 'OUTPUT' in result:
             return result['OUTPUT']
        else:
             return result['OUTPUT_RASTER']

    except Exception as e:
        print(f"  -> FATAL: Heatmap algorithm execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def style_raster_layer(raster_path, colormap_name):
    """Applies a pseudocolor style using a low-level, compatible method."""
    print(f"  -> Applying '{colormap_name}' colormap and saving style...")
    layer = QgsRasterLayer(raster_path, os.path.basename(raster_path))
    if not layer.isValid():
        print("  -> Error: Failed to load the generated heatmap raster for styling.")
        return

    provider = layer.dataProvider()
    if not provider.isValid():
        print("  -> Error: Could not get raster data provider.")
        return
    stats = provider.bandStatistics(1)
    min_val = stats.minimumValue
    max_val = stats.maximumValue

    style = QgsStyle.defaultStyle()
    if colormap_name not in style.colorRampNames():
        print(f"  -> Warning: Color ramp '{colormap_name}' not found. Skipping styling.")
        return
    color_ramp = style.colorRamp(colormap_name)
    
    shader_function = QgsColorRampShader(min_val, max_val, color_ramp, QgsColorRampShader.Interpolated)
    raster_shader = QgsRasterShader()
    raster_shader.setRasterShaderFunction(shader_function)
    
    renderer = QgsSingleBandPseudoColorRenderer(provider, 1, raster_shader)
    
    layer.setRenderer(renderer)

    sld_path = os.path.splitext(raster_path)[0] + '.sld'
    layer.saveSldStyle(sld_path)
    print(f"  -> Style saved to: {os.path.basename(sld_path)}")


def main(args):
    output_dir = args.output
    if not os.path.exists(output_dir):
        print(f"Output directory does not exist. Creating it: {output_dir}")
        os.makedirs(output_dir)
    subdirectories = get_subdirectories(args.input)
    if not subdirectories: return
    print(f"\n--- Starting to process {len(subdirectories)} subdirectories ---")
    for i, subdir_path in enumerate(subdirectories):
        folder_name = os.path.basename(subdir_path)
        print(f"\n[{i+1}/{len(subdirectories)}] Processing folder: '{folder_name}'")
        output_tif_path = os.path.join(output_dir, f"{folder_name}_heatmap.tif")
        geojson_files = find_geojson_files(subdir_path)
        if not geojson_files: print(f"  -> No GeoJSON files found. Skipping."); continue
        merged_layer = merge_geojson_to_memory_layer(geojson_files)
        if not merged_layer: print(f"  -> Failed to merge GeoJSONs. Skipping."); continue
        heatmap_path = create_heatmap(merged_layer, output_tif_path, args.radius, args.pixel_size)
        if heatmap_path and os.path.exists(heatmap_path):
            style_raster_layer(heatmap_path, COLORMAP_NAME)
        else:
            print(f"  -> Heatmap generation failed for '{folder_name}'.")
    print("\n\n--- All folders processed successfully! ---")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Creates a separate heatmap GeoTIFF for each subdirectory.",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-i', '--input', type=str, required=True, help="Parent input directory.")
    parser.add_argument('-o', '--output', type=str, required=True, help="Path to the OUTPUT DIRECTORY.")
    parser.add_argument('-r', '--radius', type=float, default=1000.0, help="Heatmap radius in layer's units.\nDefault: 1000.0")
    parser.add_argument('-p', '--pixel-size', type=float, default=50.0, help="Output pixel size in layer's units.\nDefault: 50.0")
    args = parser.parse_args()

    init_qgis_app_standalone(QGIS_INSTALL_PATH)
    main(args)
    if qgs_app:
        qgs_app.exitQgis()
        print("QGIS application closed.")