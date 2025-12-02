"""
Human behavior simulation for more natural automation.
Implements variable delays, mouse movements, and human-like interactions.
"""

import time
import random
import logging
import math
from typing import Optional, Tuple
from playwright.sync_api import Page, Locator
import numpy as np

logger = logging.getLogger(__name__)


class HumanBehavior:
    """Simulates human-like behavior in browser automation."""
    
    @staticmethod
    def variable_delay(base_delay: float, variance: float = 0.3) -> float:
        """
        Generate a variable delay using Gaussian distribution.
        
        Args:
            base_delay: Base delay in seconds.
            variance: Variance factor (0.3 = ±30%).
        
        Returns:
            Delay in seconds.
        """
        # Use Gaussian distribution centered on base_delay
        std_dev = base_delay * variance
        delay = np.random.normal(base_delay, std_dev)
        
        # Ensure minimum delay
        delay = max(0.5, delay)
        
        return delay
    
    @staticmethod
    def human_delay(min_delay: float = 1.0, max_delay: float = 3.0) -> float:
        """
        Generate a random human-like delay.
        
        Args:
            min_delay: Minimum delay in seconds.
            max_delay: Maximum delay in seconds.
        
        Returns:
            Random delay between min and max.
        """
        # Use uniform distribution for more natural variation
        delay = random.uniform(min_delay, max_delay)
        return delay
    
    @staticmethod
    def sleep_with_variance(base_delay: float, variance: float = 0.3) -> None:
        """
        Sleep for a variable amount of time.
        
        Args:
            base_delay: Base delay in seconds.
            variance: Variance factor.
        """
        delay = HumanBehavior.variable_delay(base_delay, variance)
        time.sleep(delay)
    
    @staticmethod
    def human_sleep(min_delay: float = 1.0, max_delay: float = 3.0) -> None:
        """
        Sleep for a random human-like duration.
        
        Args:
            min_delay: Minimum delay in seconds.
            max_delay: Maximum delay in seconds.
        """
        delay = HumanBehavior.human_delay(min_delay, max_delay)
        time.sleep(delay)
    
    @staticmethod
    def generate_mouse_path(start: Tuple[float, float], 
                           end: Tuple[float, float], 
                           num_points: int = 10) -> list:
        """
        Generate a human-like mouse movement path using Bezier curve.
        
        Args:
            start: Starting (x, y) coordinates.
            end: Ending (x, y) coordinates.
            num_points: Number of points in the path.
        
        Returns:
            List of (x, y) coordinates.
        """
        # Add some randomness to control points
        mid_x = (start[0] + end[0]) / 2 + random.uniform(-50, 50)
        mid_y = (start[1] + end[1]) / 2 + random.uniform(-50, 50)
        
        points = []
        for i in range(num_points + 1):
            t = i / num_points
            # Quadratic Bezier curve
            x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * mid_x + t ** 2 * end[0]
            y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * mid_y + t ** 2 * end[1]
            points.append((x, y))
        
        return points
    
    @staticmethod
    def move_mouse_human_like(page: Page, 
                             start_x: float, 
                             start_y: float, 
                             end_x: float, 
                             end_y: float) -> None:
        """
        Move mouse in a human-like trajectory.
        
        Args:
            page: Playwright page object.
            start_x: Starting X coordinate.
            start_y: Starting Y coordinate.
            end_x: Ending X coordinate.
            end_y: Ending Y coordinate.
        """
        try:
            path = HumanBehavior.generate_mouse_path(
                (start_x, start_y), 
                (end_x, end_y)
            )
            
            # Move mouse along path
            for x, y in path:
                page.mouse.move(x, y)
                time.sleep(random.uniform(0.01, 0.03))
        except Exception as e:
            logger.debug(f"Error in mouse movement: {e}")
            # Fallback: just move directly
            try:
                page.mouse.move(end_x, end_y)
            except:
                pass
    
    @staticmethod
    def click_with_human_behavior(page: Page, 
                                  locator: Locator, 
                                  move_mouse: bool = True) -> None:
        """
        Click an element with human-like behavior.
        
        Args:
            page: Playwright page object.
            locator: Element locator to click.
            move_mouse: Whether to move mouse before clicking.
        """
        try:
            # Get element bounding box
            box = locator.bounding_box()
            if not box:
                # Fallback to simple click
                locator.click()
                return
            
            center_x = box['x'] + box['width'] / 2
            center_y = box['y'] + box['height'] / 2
            
            # Add small random offset (humans don't click exactly center)
            offset_x = random.uniform(-5, 5)
            offset_y = random.uniform(-5, 5)
            click_x = center_x + offset_x
            click_y = center_y + offset_y
            
            if move_mouse:
                # Get current mouse position (approximate)
                current_x = center_x - random.uniform(50, 100)
                current_y = center_y - random.uniform(50, 100)
                
                # Move mouse to element
                HumanBehavior.move_mouse_human_like(
                    page, current_x, current_y, click_x, click_y
                )
            
            # Small delay before click
            time.sleep(random.uniform(0.1, 0.3))
            
            # Click
            page.mouse.click(click_x, click_y)
            
            # Small delay after click
            time.sleep(random.uniform(0.1, 0.2))
            
        except Exception as e:
            logger.debug(f"Error in human-like click: {e}")
            # Fallback to simple click
            try:
                locator.click()
            except:
                pass
    
    @staticmethod
    def scroll_human_like(page: Page, 
                        direction: str = 'down', 
                        amount: Optional[int] = None) -> None:
        """
        Scroll the page in a human-like manner.
        
        Args:
            page: Playwright page object.
            direction: 'up' or 'down'.
            amount: Scroll amount in pixels (random if None).
        """
        try:
            if amount is None:
                amount = random.randint(200, 800)
            
            if direction == 'down':
                amount = abs(amount)
            else:
                amount = -abs(amount)
            
            # Scroll in multiple small steps (more human-like)
            steps = random.randint(3, 6)
            step_size = amount / steps
            
            for _ in range(steps):
                page.mouse.wheel(0, step_size)
                time.sleep(random.uniform(0.1, 0.3))
        
        except Exception as e:
            logger.debug(f"Error in human-like scroll: {e}")
            # Fallback to simple scroll
            try:
                page.mouse.wheel(0, amount or 300)
            except:
                pass
    
    @staticmethod
    def type_human_like(page: Page, 
                       selector: str, 
                       text: str, 
                       typing_speed: float = 0.1) -> None:
        """
        Type text with human-like speed variation.
        
        Args:
            page: Playwright page object.
            selector: Element selector.
            text: Text to type.
            typing_speed: Base typing speed in seconds per character.
        """
        try:
            # Focus element
            page.locator(selector).focus()
            time.sleep(random.uniform(0.1, 0.3))
            
            # Type character by character with variation
            for char in text:
                page.keyboard.type(char)
                # Variable delay between characters
                delay = typing_speed * random.uniform(0.5, 1.5)
                time.sleep(delay)
        
        except Exception as e:
            logger.debug(f"Error in human-like typing: {e}")
            # Fallback to simple type
            try:
                page.locator(selector).fill(text)
            except:
                pass

