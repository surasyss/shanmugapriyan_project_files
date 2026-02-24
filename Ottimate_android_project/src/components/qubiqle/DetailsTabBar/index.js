import React from 'react';
import {
  Text,
  View,
  TouchableOpacity,
} from 'react-native';
import styles from './styles';

class DetailsTabBar extends React.Component {
    icons = [];

    views = [];

    constructor(props) {
      super(props);
      this.icons = [];
      this.views = [];
    }

    componentDidMount() {
      this.listener = this.props.scrollValue.addListener(this.setAnimationValue.bind(this));
    }

    setAnimationValue({ value }) {
      this.views.forEach((view, index) => {
        const progress = (value - index >= 0 && value - index <= 1) ? value - index : 1;
        if (view) {
          view.setNativeProps({
            style: {
              backgroundColor: this.backgroundColor(progress),
            },
          });
        }
        if (this.icons[index]) {
          this.icons[index].setNativeProps({
            style: {
              color: this.iconColor(progress)
            }
          });
        }
      });
    }

    // color between rgb(0,0,0) and rgb(143,142,148)
    iconColor(progress) {
      const red = 0 + (143 - 0) * progress;
      const green = 0 + (142 - 0) * progress;
      const blue = 0 + (148 - 0) * progress;
      return `rgb(${red}, ${green}, ${blue})`;
    }

    // color between rgb(255,255,255) and rgb(236,241,247)
    backgroundColor(progress) {
      const red = 255 + (236 - 255) * progress;
      const green = 255 + (241 - 255) * progress;
      const blue = 255 + (247 - 255) * progress;
      return `rgb(${red}, ${green}, ${blue})`;
    }

    render() {
      return (
        <View style={[styles.tabs, this.props.style]}>
          {this.props.tabs.map((tab, i) => (
            <TouchableOpacity
              key={tab}
              onPress={() => this.props.goToPage(i)}
              style={[styles.tab, { backgroundColor: this.props.activeTab === i ? 'rgb(255,255,255)' : 'rgb(236,241,247)' }]}
              ref={(view) => { this.views[i] = view; }}
              activeOpacity={1}
            >
              <Text ref={(icon) => { this.icons[i] = icon; }} style={this.props.activeTab === i ? styles.tabTextSelected : styles.tabTextUnSelected}>
                {tab}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      );
    }
}

export default DetailsTabBar;
