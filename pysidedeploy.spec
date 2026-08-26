[app]
title = json-to-pdf
project_dir = .
input_file = src/json_to_pdf
exec_directory = dist
project_file =
icon =

[python]
python_path = python
packages = Nuitka==4.1.1
android_packages =

[qt]
qml_files =
excluded_qml_plugins =
modules = Core,Gui,Widgets,PrintSupport,Pdf
plugins = accessiblebridge,egldeviceintegrations,generic,iconengines,imageformats,platforminputcontexts,platforms,platforms/darwin,platformthemes,printsupport,styles,wayland-decoration-client,wayland-graphics-integration-client,wayland-shell-integration,xcbglintegrations

[android]
wheel_pyside =
wheel_shiboken =
plugins =

[nuitka]
macos.permissions =
mode = standalone
extra_args = --quiet --noinclude-qt-translations --python-flag=-m --output-filename=json-to-pdf --include-data-dir=src/json_to_pdf/assets/fonts=json_to_pdf/assets/fonts --include-data-files=THIRD_PARTY_NOTICES.md=THIRD_PARTY_NOTICES.md

[buildozer]
mode = debug
recipe_dir =
jars_dir =
ndk_path =
sdk_path =
local_libs =
arch =
