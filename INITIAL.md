## FEATURE:

I want to build an UI that will be able to import pcb frabication files that will show a preview of the pcb.  
The preview should support layers and LaserPCB will be a cross-platform desktop CAM tool that takes standard Gerber/Excellon PCB data and turns it into fibre-laser “marking” jobs, eliminating the mess of CNC milling or wet chemistry. 
Built in Python 3 with a Qt 6 GUI, it re-uses the parsing workflow popularised by FlatCAM —import, layer mapping, CAM operations— but swaps the spindle-G-code backend for a galvo-laser engine that streams XY2-100 packets over raw USB (PyUSB/libusb) to BJJCZ LMCV4-series controllers. 
There should be a laser ui for the settings and the overall job  (pcb cutting etching)
Remember that we are going to try to keep the geometeries correctly sized IE a 2mm trace, the laser would need to remove the material around the trace but make sure the 2mm trace is the same size still.  
Will need settings for the job to help achieve the look and function of the pcb by the user.
Geometry is handled with Shapely, hatching and tool-path optimisation with NumPy/networkx, and everything is wrapped in a plug-in architecture so new lasers or recipes can be added later. 
In short: familiar FlatCAM ergonomics, but optimised for fibre machines. 

## EXAMPLES:

- examples/gerbers/ folder there are test gerber files you can use to test our code
- examples/laser_possible_settings.txt has the laser settings from a popular galvo laser software as an example.

## DOCUMENTATION:

In the examples/pybalor_driver_example.py is the whole source code for a working python driver to drive the galvo laser we will be using.  You can use this as
an example on how to write out own driver to work with our system.

The gerber specficication file is located in examples/gerber_spec.md, you can refer to this for valid and up to date gerber file syntax and operation details.

in examples/FlatCAM is the whole source code for FlatCAM

Pydantic AI documentation
[List out any documentation (web pages, sources for an MCP server like Crawl4AI RAG, etc.) that will need to be referenced during development]

## OTHER CONSIDERATIONS:

- Do not create temporary test files to determine if something is working.
- Write pytest's always when testing.
- When creating new files or directories make sure they are not duplicated and in the wrong spot.
- README with instrudctions for setup.
- Include the project structure in the README.
- Setup a venv  and pyproject.toml and requirements files
- Use the brave search MCP server to get additional information when needed.
