import ngrok

# Set your authtoken once (or configure it globally)
ngrok.set_auth_token("3DLR9lt2IK0KFQU8xvEg1poNyHr_76gPb9o8eZkah9n3uSJG3")

listener = ngrok.forward(8000)

print("Public URL:", listener.url())

input("Press Enter to stop the tunnel...")