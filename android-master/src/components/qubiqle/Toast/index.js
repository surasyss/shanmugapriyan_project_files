import React, { Component } from 'react';
import {
  View, Text, Animated, StyleSheet
} from 'react-native';

import PropTypes from 'prop-types';
import Colors from '../../../styles/Colors';

class Toast extends Component {
  constructor() {
    super();

    this.animateTranslate = new Animated.Value(-10);

    this.animateOpacity = new Animated.Value(0);

    this.state = { renderToast: false };

    this.isShownToast = false;

    this.message = '';
  }

  componentWillUnmount() {
    if (this.timerID) {
      clearTimeout(this.timerID);
    }
  }

    hideToast = (duration) => {
      this.timerID = setTimeout(() => {
        Animated.parallel([
          Animated.timing(
            this.animateTranslate,
            {
              toValue: 10,
              duration: 350
            }
          ),

          Animated.timing(
            this.animateOpacity,
            {
              toValue: 0,
              duration: 350
            }
          )
        ]).start(() => {
          this.setState({ renderToast: false });
          this.animateTranslate.setValue(-10);
          this.isShownToast = false;
          clearTimeout(this.timerID);
        });
      }, duration);
    };

    showToast(message = '', duration = 3000) {
      if (this.isShownToast === false) {
        this.message = message;

        this.isShownToast = true;

        this.setState({ renderToast: true }, () => {
          Animated.parallel([
            Animated.timing(
              this.animateTranslate,
              {
                toValue: 0,
                duration: 350
              }
            ),

            Animated.timing(
              this.animateOpacity,
              {
                toValue: 1,
                duration: 350
              }
            )
          ]).start(this.hideToast(duration));
        });
      }
    }

    render() {
      const {
        position, backgroundColor, textColor, borderColor
      } = this.props;

      if (this.state.renderToast) {
        return (
          <Animated.View
            style={[
              styles.animatedToastViewContainer,
              {
                top: (position === 'bottom') ? '80%' : '15%',
                opacity: this.animateOpacity
              }]}
            pointerEvents="none"
          >
            <View
              style={[
                styles.animatedToastView,
                { backgroundColor },
                { borderWidth: 1, borderColor },
                { borderLeftWidth: 10, borderLeftColor: borderColor }
              ]}
            >
              <Text
                numberOfLines={1}
                style={[styles.toastText, { color: textColor }]}
              >
                { this.message }
              </Text>
            </View>
          </Animated.View>
        );
      }

      return null;
    }
}

Toast.propTypes = {
  backgroundColor: PropTypes.string,
  // eslint-disable-next-line react/require-default-props
  position: PropTypes.oneOf([
    'top',
    'bottom'
  ]),
  textColor: PropTypes.string,
  borderColor: PropTypes.string
};

Toast.defaultProps = {
  backgroundColor: Colors.white,
  textColor: Colors.gray,
  borderColor: Colors.gray
};

const styles = StyleSheet.create({
  animatedToastViewContainer: {
    width: '100%',
    zIndex: 9999,
    position: 'absolute'
  },

  animatedToastView: {
    marginHorizontal: 30,
    paddingHorizontal: 25,
    paddingVertical: 10,
    borderRadius: 5,
    justifyContent: 'center',
    alignSelf: 'center'
  },

  toastText: {
    marginTop: 10,
    marginBottom: 10,
    fontSize: 18,
    alignSelf: 'stretch',
    textAlign: 'center',
    backgroundColor: 'transparent'
  }
});

export default Toast;
