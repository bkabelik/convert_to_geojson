import os
import json
import argparse
import sys

def process_json_file(input_path, output_path):
    """
    Reads a JSON file in the specified format, extracts track data and metadata,
    and writes it to a new GeoJSON file.

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

    # The final GeoJSON will be a FeatureCollection containing all tracks from the file.
    final_features = []

    # The top-level key is "items", which is a list.
    # Using .get() is safer than direct access in case the key is missing.
    items = data.get("items", [])
    if not isinstance(items, list):
        print(f"Warning: 'items' key in {input_path} is not a list. Skipping file.")
        return False

    for item in items:
        # Each item has user metadata and a list of tracks.
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
            # The actual geometry is inside track_item["track"]["features"]
            # It's already in GeoJSON Feature format, which is very convenient.
            inner_feature_collection = track_item.get("track")
            if not inner_feature_collection or 'features' not in inner_feature_collection:
                print(f"Warning: No 'track' or 'features' found for a track by user {user_id} in {input_path}. Skipping track.")
                continue
            
            # This is the list of features (likely just one LineString) for this specific track.
            for feature in inner_feature_collection.get("features", []):
                # We will enrich the feature's properties with all the metadata.
                # Start with any existing properties the feature might have.
                new_properties = feature.get("properties", {}).copy()

                # Add user properties
                new_properties.update(user_properties)

                # Add track-specific properties
                new_properties["trackId"] = track_item.get("trackId")
                new_properties["activity"] = track_item.get("activity")
                new_properties["locationCountry"] = track_item.get("locationCountry")
                
                # Add summary and resort info as nested objects for better organization
                new_properties["summary"] = track_item.get("summary")
                new_properties["resort"] = track_item.get("resort")

                # Update the feature with the new, enriched properties
                feature["properties"] = new_properties
                
                # Add the fully processed feature to our final list
                final_features.append(feature)

    if not final_features:
        print(f"Info: No valid track features found in {input_path}. No output file will be created.")
        return False

    # Create the final GeoJSON FeatureCollection structure
    output_geojson = {
        "type": "FeatureCollection",
        "features": final_features
    }

    # Write the beautiful, new GeoJSON file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Use indent for human-readable output
            json.dump(output_geojson, f, indent=2)
    except IOError as e:
        print(f"Error: Could not write to output file {output_path}. Reason: {e}")
        return False
        
    return True


def convert_directory_to_geojson(input_dir, output_dir):
    """
    Finds all .json files in an input directory, converts them to GeoJSON,
    and saves them in the output directory.

    Args:
        input_dir (str): Path to the directory containing source JSON files.
        output_dir (str): Path to the directory where GeoJSON files will be saved.
    """
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' not found.")
        sys.exit(1)

    # Create the output directory if it doesn't exist
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
            output_filename = f"{base_name}.geojson"
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
        description="Converts a directory of specific JSON files to GeoJSON format.",
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
    
    convert_directory_to_geojson(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()