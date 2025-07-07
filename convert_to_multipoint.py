import os
import json
import argparse
import sys

def process_json_file(input_path, output_path):
    """
    Reads a JSON file, finds all LineString tracks, and converts each
    one into a MultiPoint feature in a single output GeoJSON file.

    Args:
        input_path (str): The full path to the input JSON file.
        output_path (str): The full path for the output GeoJSON file.
    
    Returns:
        bool: True if conversion was successful, False otherwise.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file {input_path}")
        return False
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
        return False

    # This list will hold all the new MultiPoint features.
    all_multipoint_features = []

    items = data.get("items", [])
    if not isinstance(items, list):
        print(f"Warning: 'items' key in {input_path} is not a list. Skipping file.")
        return False

    for item in items:
        user_id = item.get("userId")
        user_properties = {
            "userId": user_id,
            "ageGroup": item.get("ageGroup"),
            "countryCode": item.get("countryCode"),
            "gender": item.get("gender")
        }

        tracks = item.get("tracks", [])
        if not isinstance(tracks, list):
            print(f"Warning: 'tracks' key for user {user_id} in {input_path} is not a list. Skipping user.")
            continue

        for track_item in tracks:
            inner_feature_collection = track_item.get("track")
            if not inner_feature_collection or 'features' not in inner_feature_collection:
                print(f"Warning: No 'track' or 'features' found for a track by user {user_id}. Skipping.")
                continue
            
            # This is the list of features (likely one LineString) for this track.
            for feature in inner_feature_collection.get("features", []):
                # We only care about converting LineStrings
                if feature.get("geometry", {}).get("type") != "LineString":
                    continue
                
                # --- 1. Assemble all properties for the track ---
                # These properties will be applied to the new MultiPoint feature.
                track_properties = feature.get("properties", {}).copy()
                track_properties.update(user_properties)
                track_properties["trackId"] = track_item.get("trackId")
                track_properties["activity"] = track_item.get("activity")
                track_properties["locationCountry"] = track_item.get("locationCountry")
                track_properties["summary"] = track_item.get("summary")
                track_properties["resort"] = track_item.get("resort")

                # --- 2. Create the new MultiPoint geometry ---
                # The coordinate array from a LineString is exactly what a MultiPoint needs.
                multipoint_geometry = {
                    "type": "MultiPoint",
                    "coordinates": feature["geometry"].get("coordinates", [])
                }

                # --- 3. Create the new MultiPoint Feature ---
                multipoint_feature = {
                    "type": "Feature",
                    "geometry": multipoint_geometry,
                    "properties": track_properties
                }
                
                all_multipoint_features.append(multipoint_feature)

    if not all_multipoint_features:
        print(f"Info: No valid LineString features found in {input_path} to convert. No output file created.")
        return False

    # Create the final GeoJSON FeatureCollection structure
    output_geojson = {
        "type": "FeatureCollection",
        "features": all_multipoint_features
    }

    # Write the new GeoJSON file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_geojson, f, indent=2)
    except IOError as e:
        print(f"Error: Could not write to output file {output_path}. Reason: {e}")
        return False
        
    return True


def convert_directory_to_multipoint(input_dir, output_dir):
    """
    Finds all .json files in a directory, converts their LineStrings to
    MultiPoints, and saves them as new GeoJSON files.
    """
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' not found.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    print(f"Output will be saved in: {os.path.abspath(output_dir)}")

    file_count = 0
    success_count = 0

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".json"):
            file_count += 1
            input_filepath = os.path.join(input_dir, filename)
            
            # Create a corresponding output filename
            base_name = os.path.splitext(filename)[0]
            output_filename = f"{base_name}_multipoint.geojson"
            output_filepath = os.path.join(output_dir, output_filename)

            print(f"\nProcessing '{filename}'...")
            if process_json_file(input_filepath, output_filepath):
                print(f"Successfully converted to '{output_filename}'")
                success_count += 1
            else:
                print(f"Failed to convert '{filename}'")

    print("\n--- Conversion Summary ---")
    print(f"Total .json files found: {file_count}")
    print(f"Successfully converted: {success_count}")
    print(f"Failed or skipped: {file_count - success_count}")
    print("--------------------------")


def main():
    """Main function to parse arguments and start the conversion."""
    parser = argparse.ArgumentParser(
        description="Converts LineStrings in specific JSON files to MultiPoint GeoJSON format.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_dir",
        help="The path to the directory containing the input JSON files."
    )
    parser.add_argument(
        "-o", "--output_dir",
        default="geojson_output",
        help="The path to the directory where GeoJSON files will be saved.\n(default: 'geojson_output' in the current directory)"
    )

    args = parser.parse_args()
    convert_directory_to_multipoint(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()