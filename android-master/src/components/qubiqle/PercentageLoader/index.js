/* eslint-disable */

import React, { Component } from 'react';
import {
  View,
  Text,
} from 'react-native';
import styles from './styles';


class PercentageLoader extends Component {
  constructor(props) {
    super(props);
    const { percent } = this.props;
    let leftTransformerDegree = '0deg';
    let rightTransformerDegree = '0deg';
    if (percent >= 50) {
      rightTransformerDegree = '180deg';
      leftTransformerDegree = `${(percent - 50) * 3.6}deg`;
    } else {
      rightTransformerDegree = `${percent * 3.6}deg`;
      leftTransformerDegree = '0deg';
    }

    this.state = {
      percent: this.props.percent,
      borderWidth: this.props.borderWidth < 2 || !this.props.borderWidth ? 2 : this.props.borderWidth,
      leftTransformerDegree,
      rightTransformerDegree,
      textStyle: this.props.textStyle ? this.props.textStyle : null
    };
  }

  componentWillReceiveProps(nextProps) {
    const { percent } = nextProps;
    let leftTransformerDegree = '0deg';
    let rightTransformerDegree = '0deg';
    if (percent >= 50) {
      rightTransformerDegree = '180deg';
      leftTransformerDegree = `${(percent - 50) * 3.6}deg`;
    } else {
      rightTransformerDegree = `${percent * 3.6}deg`;
    }
    this.setState({
      percent: this.props.percent,
      borderWidth: this.props.borderWidth < 2 || !this.props.borderWidth ? 2 : this.props.borderWidth,
      leftTransformerDegree,
      rightTransformerDegree
    });
  }

  render() {
    if (this.props.disabled) {
      return (
        <View style={[styles.circle, {
          width: this.props.radius * 2,
          height: this.props.radius * 2,
          borderRadius: this.props.radius
        }]}
        >
          <Text style={styles.text}>{this.props.disabledText}</Text>
        </View>
      );
    }
    return (
      <View style={[styles.circle, {
        width: this.props.radius * 2,
        height: this.props.radius * 2,
        borderRadius: this.props.radius,
        backgroundColor: this.props.bgcolor
      }]}
      >
        <View style={[styles.leftWrap, {
          width: this.props.radius,
          height: this.props.radius * 2,
          left: 0,
        }]}
        >
          <View style={[styles.loader, {
            left: this.props.radius,
            width: this.props.radius,
            height: this.props.radius * 2,
            borderTopLeftRadius: 0,
            borderBottomLeftRadius: 0,
            backgroundColor: this.props.color,
            transform: [{ translateX: -this.props.radius / 2 }, { rotate: this.state.leftTransformerDegree }, { translateX: this.props.radius / 2 }],
          }]}
          />
        </View>
        <View style={[styles.leftWrap, {
          left: this.props.radius,
          width: this.props.radius,
          height: this.props.radius * 2,
        }]}
        >
          <View style={[styles.loader, {
            left: -this.props.radius,
            width: this.props.radius,
            height: this.props.radius * 2,
            borderTopRightRadius: 0,
            borderBottomRightRadius: 0,
            backgroundColor: this.props.color,
            transform: [{ translateX: this.props.radius / 2 }, { rotate: this.state.rightTransformerDegree }, { translateX: -this.props.radius / 2 }],
          }]}
          />
        </View>
        <View style={[styles.innerCircle, {
          width: (this.props.radius - this.state.borderWidth) * 2,
          height: (this.props.radius - this.state.borderWidth) * 2,
          borderRadius: this.props.radius - this.state.borderWidth,
          backgroundColor: this.props.innerColor,
        }]}
        >
          {this.props.children ? this.props.children
            : (
              <Text style={[styles.text, this.state.textStyle]}>
                {this.props.percent}
%
              </Text>
            )}
        </View>

      </View>
    );
  }
}

// set some attributes default value
PercentageLoader.defaultProps = {
  bgcolor: '#e3e3e3',
  innerColor: '#fff'
};

module.exports = PercentageLoader;
