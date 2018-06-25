
import React from 'react'
import { Switch, Route } from 'react-router-dom'
import styled from 'styled-components'

export class HeaderComponent extends React.Component {

  render() {
    const Style = styled.div`
      display: flex;
      justify-content: space-between;
      align-items: center;
      height: 3em;
      padding: 1em;

      background-color: #323232;
      color: white;

      .brand {
        font-weight: bold;
        font-size: 200%;
      }
      .server-name {
      }
    `
    return <Style>
      <span className="brand">Discord Music Bot</span>
      <Switch>
        <Route path="/server/:server" component={(props) => (
          <div>{props.match.params.server}</div>
        )}/>
      </Switch>
    </Style>
  }

}
