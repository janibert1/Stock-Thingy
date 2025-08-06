def background_updates():
    while True:
        
        record_portfolio_worth()
        
        time.sleep(60),
def live_update():
    while True:

        value = totaltotal()        
        socketio.emit('update', {'value': value})
        time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=background_updates, daemon=True).start()
    threading.Thread(target=live_update, daemon=True ).start()
    socketio.run(app, debug=True, port=8080)
    # Stock-Thingy
