// Minimal structured logger for Mini Program
// Usage: import logger from '~/utils/logger'; logger.info('message', {key: 'value'})

function fmt(level, msg, ctx) {
  const ts = new Date().toISOString();
  let line = `[${ts}] ${level.toUpperCase()} ${msg}`;
  if (ctx !== undefined) {
    try {
      const extra = typeof ctx === 'string' ? ctx : JSON.stringify(ctx);
      line += ' ' + extra;
    } catch (e) {
      // fallback
      line += ' [unserializable-context]';
    }
  }
  return line;
}

const logger = {
  debug(msg, ctx) {
    try { console.debug(fmt('debug', msg, ctx)); } catch (_) {}
  },
  info(msg, ctx) {
    try { console.log(fmt('info', msg, ctx)); } catch (_) {}
  },
  warn(msg, ctx) {
    try { console.warn(fmt('warn', msg, ctx)); } catch (_) {}
  },
  error(msg, ctx) {
    try { console.error(fmt('error', msg, ctx)); } catch (_) {}
  },
};

export default logger;

