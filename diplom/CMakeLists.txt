# CMakeList.txt: проект CMake для diplom; включите исходный код и определения,
# укажите здесь логику для конкретного проекта.
#

# Добавьте источник в исполняемый файл этого проекта.
add_executable (diplom "diplom.cpp" "diplom.h")

if (CMAKE_VERSION VERSION_GREATER 3.12)
  set_property(TARGET diplom PROPERTY CXX_STANDARD 20)
endif()

# TODO: Добавьте тесты и целевые объекты, если это необходимо.
