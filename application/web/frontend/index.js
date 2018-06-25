
import React from 'react'
import ReactDOM from 'react-dom'
import { BrowserRouter } from 'react-router-dom'
import styled from 'styled-components'
import './normalize.css'

import { HeaderComponent} from './HeaderComponent'

export class App extends React.Component {

  render() {
    const Style = styled.div`
      background-color: #212121;
      height: 100%;
    `
    return <Style>
      <HeaderComponent/>
    </Style>
  }

}


ReactDOM.render(<BrowserRouter><App/></BrowserRouter>, document.getElementById('main'))
