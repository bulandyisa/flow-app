import type { Request, Response, NextFunction } from 'express';
import { isActivated } from '../api/auth.js';

/**
 * Middleware that blocks all API routes if the app is not activated.
 * Exceptions: /api/auth/* routes are always accessible.
 */
export function requireActivation(req: Request, res: Response, next: NextFunction): void {
  // CORS preflight must never be blocked — иначе любой PATCH/DELETE падает
  // у клиента с «Failed to fetch» ещё до того как дойдёт до бизнес-логики.
  if (req.method === 'OPTIONS') {
    next();
    return;
  }

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
