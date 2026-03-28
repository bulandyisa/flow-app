import type { Request, Response, NextFunction } from 'express';
import { isActivated } from '../api/auth.js';

/**
 * Middleware that blocks all API routes if the app is not activated.
 * Exceptions: /api/auth/* routes are always accessible.
 */
export function requireActivation(req: Request, res: Response, next: NextFunction): void {
  // Allow auth routes through
  if (req.path.startsWith('/api/auth')) {
    next();
    return;
  }

  if (!isActivated()) {
    res.status(403).json({
      error: 'Приложение не активировано',
      code: 'NOT_ACTIVATED',
    });
    return;
  }

  next();
}
