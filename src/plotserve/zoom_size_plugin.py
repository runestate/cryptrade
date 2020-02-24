import mpld3


class ZoomSizePlugin(mpld3.plugins.PluginBase):
    JAVASCRIPT = r"""
    // little save icon
    var my_icon = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gUTDC0v7E0+LAAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAAAa0lEQVQoz32QQRLAIAwCA///Mz3Y6cSG4EkjoAsk1VgAqspecVP3TTIA6MHTQ6sOHm7Zm4dWHcC4wc3hmVzT7xEbYf66dX/xnEOI7M9KYgie6qvW6ZH0grYOmQGOxzCEQn8C5k5mHAOrbeIBWLlaA3heUtcAAAAASUVORK5CYII=";
    // create plugin
    mpld3.register_plugin("zoomSize", ZoomSizePlugin);
    ZoomSizePlugin.prototype = Object.create(mpld3.Plugin.prototype);
    ZoomSizePlugin.prototype.constructor = ZoomSizePlugin;
    ZoomSizePlugin.prototype.requiredProps = [];
    ZoomSizePlugin.prototype.defaultProps = {}
    function ZoomSizePlugin(fig, props){
        mpld3.Plugin.call(this, fig, props);
        console.log(fig)
        mpld3.getPlotZoomWindow = function() {
		      var ax= fig.axes[0]
		      return {
		      	x_min: ax.xdom.invert(0),
		      	x_max: ax.xdom.invert(ax.width)
		      }
        }
        // create save button
        var SaveButton = mpld3.ButtonFactory({
            buttonID: "save",
            sticky: false,
            onActivate: function(){save_zoom(fig);}.bind(this),
            icon: function(){return my_icon;},
        });
        this.fig.buttons.push(SaveButton);
    };
    function save_zoom(fig) {
      console.log('abekat');
      console.log(fig.axes)
      var ax= fig.axes[0],
          extent = "";
      console.log(ax);
      console.log(ax.xdom.invert(0));
      console.log(ax.xdom.invert(ax.width));
    }
    """
    def __init__(self):
        self.dict_ = {"type": "zoomSize"}
