test_square = '''
<!-- Created with tg-plot (v4) at 20241010_210611.777_UTC+1 -->
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:tg="https://sketch.process.studio/turtle-graphics"
     xmlns:serif="http://www.serif.com/"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     tg:version="4" tg:count="8" tg:layer_count="1" tg:oob_count="0" tg:short_count="0" tg:travel="1762" tg:travel_ink="1236" tg:travel_blank="525" tg:format="A4 Landscape" tg:width_mm="297" tg:height_mm="210" tg:speed="100" tg:author="" tg:timestamp="20241010_210611.777_UTC+1"
     width="297mm"
     height="210mm"
     viewBox="-148.5 -105 297 210"
     stroke="black" fill="none" stroke-linecap="round">
    <g id="Layer 0" stroke="black" serif:id="Layer 0" inkscape:groupmode="layer" inkscape:label="0 Layer 0">
        <path d="M -99.75 -99.75 L 99.75 -99.75 99.75 99.75 -99.75 99.75 -99.75 -99.75 M 0 99.75 L 0 -99.75 M -99.75 0 L 99.75 0 M 0 -99.75 L 14.107 -85.643 M 0 -99.75 L -14.107 -85.643" />
    </g>
</svg>
'''

test_wide = '''
<!-- Created with tg-plot (v4) at 20241010_210706.254_UTC+1 -->
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:tg="https://sketch.process.studio/turtle-graphics"
     xmlns:serif="http://www.serif.com/"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     tg:version="4" tg:count="8" tg:layer_count="1" tg:oob_count="0" tg:short_count="0" tg:travel="1848" tg:travel_ink="1311" tg:travel_blank="536" tg:format="A4 Landscape" tg:width_mm="297" tg:height_mm="210" tg:speed="100" tg:author="" tg:timestamp="20241010_210706.254_UTC+1"
     width="297mm"
     height="210mm"
     viewBox="-148.5 -105 297 210"
     stroke="black" fill="none" stroke-linecap="round">
    <g id="Layer 0" stroke="black" serif:id="Layer 0" inkscape:groupmode="layer" inkscape:label="0 Layer 0">
        <path d="M -141.075 -70.537 L 141.075 -70.537 141.075 70.538 -141.075 70.538 -141.075 -70.537 M 0 70.538 L 0 -70.537 M -141.075 0 L 141.075 0 M 0 -70.537 L 14.964 -55.574 M 0 -70.537 L -14.964 -55.574" />
    </g>
</svg>
'''

test_high = '''
<!-- Created with tg-plot (v4) at 20241010_210745.687_UTC+1 -->
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:tg="https://sketch.process.studio/turtle-graphics"
     xmlns:serif="http://www.serif.com/"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     tg:version="4" tg:count="8" tg:layer_count="1" tg:oob_count="0" tg:short_count="0" tg:travel="1371" tg:travel_ink="927" tg:travel_blank="443" tg:format="A4 Landscape" tg:width_mm="297" tg:height_mm="210" tg:speed="100" tg:author="" tg:timestamp="20241010_210745.687_UTC+1"
     width="297mm"
     height="210mm"
     viewBox="-148.5 -105 297 210"
     stroke="black" fill="none" stroke-linecap="round">
    <g id="Layer 0" stroke="black" serif:id="Layer 0" inkscape:groupmode="layer" inkscape:label="0 Layer 0">
        <path d="M -49.875 -99.75 L 49.875 -99.75 49.875 99.75 -49.875 99.75 -49.875 -99.75 M 0 99.75 L 0 -99.75 M -49.875 0 L 49.875 0 M 0 -99.75 L 10.58 -89.17 M 0 -99.75 L -10.58 -89.17" />
    </g>
</svg>
'''

test_layers = '''
<!-- Created with tg-plot (v4) at 20241010_210810.915_UTC+1 -->
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:tg="https://sketch.process.studio/turtle-graphics"
     xmlns:serif="http://www.serif.com/"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     tg:version="4" tg:count="8" tg:layer_count="3" tg:oob_count="0" tg:short_count="0" tg:travel="1762" tg:travel_ink="1236" tg:travel_blank="525" tg:format="A4 Landscape" tg:width_mm="297" tg:height_mm="210" tg:speed="100" tg:author="" tg:timestamp="20241010_210810.915_UTC+1"
     width="297mm"
     height="210mm"
     viewBox="-148.5 -105 297 210"
     stroke="black" fill="none" stroke-linecap="round">
    <g id="Layer 0" stroke="black" serif:id="Layer 0" inkscape:groupmode="layer" inkscape:label="0 Layer 0">
        <path d="M -99.75 -99.75 L 99.75 -99.75 99.75 99.75 -99.75 99.75 -99.75 -99.75" />
    </g>
    <g id="Layer 1" stroke="red" serif:id="Layer 1" inkscape:groupmode="layer" inkscape:label="!1 Layer 1">
        <path d="M 0 99.75 L 0 -99.75 M -99.75 0 L 99.75 0" />
    </g>
    <g id="Layer 2" stroke="orange" serif:id="Layer 2" inkscape:groupmode="layer" inkscape:label="!2 Layer 2">
        <path d="M 0 -99.75 L 14.107 -85.643 M 0 -99.75 L -14.107 -85.643" />
    </g>
</svg>
'''

from spooler import svg_to_job
import uuid

def test_job(name = 'layers'):
    svg = globals()['test_' + name]
    client = 'Test-' + uuid.uuid4().hex[:3]
    svg = svg.replace('tg:author=""', f'tg:author="{client}"')
    job = svg_to_job(svg)
    return job
