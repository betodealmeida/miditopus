"""
A MIDI inter-connector.
"""

import hashlib
import re
import threading
import time
from collections import defaultdict
from typing import Dict, Set

import mido
import pygame
from pygame._sdl2 import touch


def update_ports(
    inputs: Set[str],
    outputs: Set[str],
    connections: Dict[str, Set[str]],
    input_ports,
    output_ports,
) -> None:
    while True:
        new_inputs = {
            name
            for name in mido.get_input_names()
            if "Midi Through Port" not in name and "RtMidi" not in name
        }
        for name in set(inputs):
            if name not in new_inputs:
                inputs.remove(name)
                if name in connections:
                    del connections[name]
                if name in input_ports:
                    del input_ports[name]
        for name in new_inputs:
            if name not in inputs:
                inputs.add(name)

        new_outputs = {
            name
            for name in mido.get_output_names()
            if "Midi Through Port" not in name and "RtMidi" not in name
        }
        for name in set(outputs):
            if name not in new_outputs:
                outputs.remove(name)
                for targets in connections.values():
                    if name in targets:
                        targets.remove(name)
                if name in output_ports:
                    del output_ports[name]
        for name in new_outputs:
            if name not in outputs:
                outputs.add(name)

        time.sleep(1)


def main() -> None:
    """
    Main loop.
    """
    pygame.init()

    font = pygame.font.SysFont(None, 24)
    screen = pygame.display.set_mode([800, 480])
    width, height = screen.get_size()
    # screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    colors = [
        "#00B7FF",
        "#004DFF",
        "#00FFFF",
        "#826400",
        "#580041",
        "#FF00FF",
        "#00FF00",
        "#C500FF",
        "#B4FFD7",
        "#FFCA00",
        "#969600",
        "#B4A2FF",
        "#C20078",
        "#0000C1",
        "#FF8B00",
        "#FFC8FF",
        "#666666",
        "#FF0000",
        "#CCCCCC",
        "#009E8F",
        "#D7A870",
        "#8200FF",
        "#960000",
        "#BBFF00",
        "#FFFF00",
        "#006F00",
    ]

    inputs = set()
    outputs = set()
    connections = defaultdict(set)
    input_ports = {}
    output_ports = {}
    thread = threading.Thread(
        target=update_ports,
        args=(inputs, outputs, connections, input_ports, output_ports),
    )
    thread.start()

    done = False
    clock = pygame.time.Clock()

    while not done:
        drag_start = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                drag_start = pos
            if event.type == pygame.MOUSEBUTTONUP:
                pos = pygame.mouse.get_pos()
                drag_start = None
                # XXX connect or disconnect

        screen.fill("white")

        # propagate messages
        for source, targets in connections.items():
            if source not in input_ports:
                input_ports[source] = mido.open_input(source)
            for message in input_ports[source].iter_pending():
                for target in targets:
                    if target not in output_ports:
                        output_ports[target] = mido.open_output(target)
                    output_ports[target].send(message)

        # show inputs
        for i, name in enumerate(sorted(inputs)):
            short_name = re.sub(".*?:(.*?)\d+:\d+", r"\1", name)
            color_index = int(hashlib.md5(name.encode()).hexdigest(), 16)
            color = colors[color_index % len(colors)]
            x0 = 0
            y0 = i * height / len(inputs)
            pygame.draw.rect(screen, color, [x0, y0, width / 2, height / len(inputs)])
            pygame.draw.rect(
                screen,
                "black",
                [x0, y0, width / 2, height / len(inputs)],
                1,
            )
            text = font.render(short_name, True, (0, 0, 0))
            text_rect = text.get_rect(
                center=(width / 4, y0 + (height / (2 * len(inputs))))
            )
            screen.blit(text, text_rect)

            for j, target in enumerate(sorted(connections[name])):
                cell_height = (height / len(inputs)) / len(connections[name])
                color_index = int(hashlib.md5(target.encode()).hexdigest(), 16)
                color = colors[color_index % len(colors)]
                x0 = (width / 2) - 20
                y0 = (i * height / len(inputs)) + (j * cell_height)
                pygame.draw.rect(screen, color, [x0, y0, 20, cell_height])
                pygame.draw.rect(screen, "black", [x0, y0, 20, cell_height], 1)

        # show outputs
        for i, name in enumerate(sorted(outputs)):
            short_name = re.sub(".*?:(.*?)\d+:\d+", r"\1", name)
            color_index = int(hashlib.md5(name.encode()).hexdigest(), 16)
            color = colors[color_index % len(colors)]
            x0 = width / 2
            y0 = i * height / len(outputs)
            pygame.draw.rect(screen, color, [x0, y0, width / 2, height / len(inputs)])
            pygame.draw.rect(
                screen,
                "black",
                [x0, y0, width / 2, height / len(inputs)],
                1,
            )
            text = font.render(short_name, True, (0, 0, 0))
            text_rect = text.get_rect(
                center=(width * 3 / 4, y0 + (height / (2 * len(inputs))))
            )
            screen.blit(text, text_rect)

        pygame.draw.line(screen, "black", (width / 2, 0), (width / 2, height))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    midi.quit()


if __name__ == "__main__":
    main()
