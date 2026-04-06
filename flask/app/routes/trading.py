from flask import Blueprint, render_template

# Blueprint für die Trading-Bot-Seite
trading_bp = Blueprint('trading', __name__)

@trading_bp.route('/trading_bot', methods=['GET'])
def trading_page():
    """Trading Bot-Seite anzeigen."""
    # Platzhalter für spätere Trading-Bot-Statistiken
    trading_stats = {
        "active_trades": 0,
        "profit_today": 0.0,
        "total_profit": 0.0
    }
    return render_template('trading.html', stats=trading_stats)
