"""Compare a reproduced run with the selected report figures by bytes and pixels."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def compare(generated_dir):
    results = []
    for name in ('fig_sim_deviation.png', 'fig_sim_belief.png'):
        reference, generated = ROOT / 'figures' / name, generated_dir / name
        with Image.open(reference) as image:
            reference_pixels = np.array(image.convert('RGBA'))
        with Image.open(generated) as image:
            generated_pixels = np.array(image.convert('RGBA'))
        equal_shape = reference_pixels.shape == generated_pixels.shape
        equal_pixels = equal_shape and np.array_equal(reference_pixels, generated_pixels)
        results.append({'filename': name,
                        'reference_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
                        'generated_sha256': hashlib.sha256(generated.read_bytes()).hexdigest(),
                        'identical_bytes': reference.read_bytes() == generated.read_bytes(),
                        'identical_decoded_RGBA_pixels': bool(equal_pixels),
                        'reference_shape': list(reference_pixels.shape), 'generated_shape': list(generated_pixels.shape),
                        'different_pixel_count': int(np.count_nonzero(np.any(reference_pixels != generated_pixels, axis=2))) if equal_shape else None})
    return {'reference_directory': 'figures', 'generated_directory': str(generated_dir),
            'note': 'Exact reproduction in this tested environment does not establish the original historical Python/NumPy environment.',
            'figures': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = compare(args.generated_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
